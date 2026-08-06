from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.anon import anon_key_from_header
from app.auth import get_current_user, get_optional_user
from app.db import db_session
from app.models import Post, PostComment, PostLike, User
from app.schemas import PostCommentIn, PostCommentOut, PostLikeOut

router = APIRouter(tags=["post-social"])


async def _get_visible_post(session: AsyncSession, post_id: int, current_user: User | None) -> Post:
    post = (await session.execute(select(Post).where(Post.id == post_id))).scalars().first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status != "published" and not (current_user and current_user.is_mod):
        raise HTTPException(status_code=404, detail="Post not found")
    return post


def _to_comment_out(comment: PostComment) -> PostCommentOut:
    return PostCommentOut(
        id=comment.id,
        post_id=comment.post_id,
        user_id=comment.user_id,
        username=comment.author.username,
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


async def _count_likes(session: AsyncSession, post_id: int) -> int:
    return (
        await session.execute(
            select(func.count()).select_from(PostLike).where(PostLike.post_id == post_id)
        )
    ).scalar_one()


# ── Comments ──────────────────────────────────────────────────────────────────

@router.get("/posts/{post_id}/comments", response_model=list[PostCommentOut])
async def list_post_comments(
    post_id: int,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(db_session),
) -> list[PostCommentOut]:
    post = await _get_visible_post(session, post_id, current_user)

    res = await session.execute(
        select(PostComment)
        .where(PostComment.post_id == post.id)
        .options(joinedload(PostComment.author))
        .order_by(PostComment.created_at.asc())
    )
    comments = res.scalars().unique().all()
    return [_to_comment_out(c) for c in comments]


@router.post("/posts/{post_id}/comments", response_model=PostCommentOut, status_code=201)
async def post_post_comment(
    post_id: int,
    payload: PostCommentIn,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
) -> PostCommentOut:
    post = await _get_visible_post(session, post_id, current_user)

    comment = PostComment(post_id=post.id, user_id=current_user.id, body=payload.body.strip())
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    return PostCommentOut(
        id=comment.id,
        post_id=comment.post_id,
        user_id=comment.user_id,
        username=current_user.username,
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.delete("/post-comments/{comment_id}", status_code=204)
async def delete_post_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
) -> None:
    res = await session.execute(select(PostComment).where(PostComment.id == comment_id))
    comment = res.scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and not current_user.is_mod:
        raise HTTPException(status_code=403, detail="Not your comment")
    await session.delete(comment)
    await session.commit()


# ── Likes ─────────────────────────────────────────────────────────────────────

@router.get("/posts/{post_id}/like", response_model=PostLikeOut)
async def get_post_like(
    post_id: int,
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(db_session),
) -> PostLikeOut:
    post = await _get_visible_post(session, post_id, current_user)

    # Identity is optional here (unlike the toggle below) — an anonymous reader
    # with no X-Client-Id yet should still see the total, just with your_liked=False.
    if current_user:
        liker_type, liker_key = "user", str(current_user.id)
    else:
        liker_type, liker_key = "anon", anon_key_from_header(x_client_id)

    your_liked = False
    if liker_key:
        existing = await session.execute(
            select(PostLike.id).where(
                PostLike.post_id == post.id,
                PostLike.liker_type == liker_type,
                PostLike.liker_key == liker_key,
            )
        )
        your_liked = existing.scalars().first() is not None

    return PostLikeOut(likes=await _count_likes(session, post.id), your_liked=your_liked)


@router.post("/posts/{post_id}/like", response_model=PostLikeOut)
async def toggle_post_like(
    post_id: int,
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(db_session),
) -> PostLikeOut:
    post = await _get_visible_post(session, post_id, current_user)

    if current_user:
        liker_type, liker_key = "user", str(current_user.id)
    else:
        liker_type = "anon"
        liker_key = anon_key_from_header(x_client_id)
        if not liker_key:
            raise HTTPException(status_code=400, detail="Missing/invalid X-Client-Id")

    existing = (
        await session.execute(
            select(PostLike).where(
                PostLike.post_id == post.id,
                PostLike.liker_type == liker_type,
                PostLike.liker_key == liker_key,
            )
        )
    ).scalars().first()

    if existing:
        await session.delete(existing)  # already liked -> unlike
    else:
        session.add(PostLike(post_id=post.id, liker_type=liker_type, liker_key=liker_key))

    await session.commit()

    return PostLikeOut(likes=await _count_likes(session, post.id), your_liked=existing is None)


@router.post("/auth/claim-anon-likes")
async def claim_anon_likes(
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
) -> dict:
    """Reassign anonymous likes (by browser UUID) to the logged-in user account."""
    anon_key = anon_key_from_header(x_client_id)
    if not anon_key:
        raise HTTPException(status_code=400, detail="Missing/invalid X-Client-Id")

    user_post_ids_res = await session.execute(
        select(PostLike.post_id).where(
            PostLike.liker_type == "user", PostLike.liker_key == str(current_user.id)
        )
    )
    already_liked = {row[0] for row in user_post_ids_res.all()}

    anon_res = await session.execute(
        select(PostLike).where(PostLike.liker_type == "anon", PostLike.liker_key == anon_key)
    )
    anon_likes = anon_res.scalars().all()

    claimed = 0
    for like in anon_likes:
        if like.post_id in already_liked:
            # User already likes this post under their account — drop the anon
            # row instead of leaving it (unlike claim-anon-votes, which leaves
            # the analogous row in place and ends up double-counting).
            await session.delete(like)
            continue
        like.liker_type = "user"
        like.liker_key = str(current_user.id)
        claimed += 1

    await session.commit()
    return {"claimed": claimed}
