from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user, get_optional_user
from app.db import db_session
from app.models import Post, PostTag, User
from app.schemas import PostIn, PostListOut, PostOut, PostSummary, TagCountOut

router = APIRouter(tags=["blog"])

WORDS_PER_MINUTE = 220
_NON_SLUG = re.compile(r"[^a-z0-9]+")
_MD_NOISE = re.compile(r"[*_`>#\[\]()!]|\!\[[^\]]*\]|\]\([^)]*\)")


def _require_mod(user: User) -> User:
    if not user.is_mod:
        raise HTTPException(status_code=403, detail="Mod access required")
    return user


def slugify(title: str) -> str:
    base = _NON_SLUG.sub("-", title.strip().lower()).strip("-")
    return base[:150] or "post"


def _plain_text(markdown: str) -> str:
    """Rough markdown strip — good enough for excerpts and word counts."""
    text = re.sub(r"```.*?```", " ", markdown, flags=re.DOTALL)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = _MD_NOISE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def reading_minutes(markdown: str) -> int:
    words = len(_plain_text(markdown).split())
    return max(1, math.ceil(words / WORDS_PER_MINUTE))


def derive_excerpt(post_excerpt: str | None, markdown: str) -> str | None:
    if post_excerpt:
        return post_excerpt
    text = _plain_text(markdown)
    if not text:
        return None
    if len(text) <= 200:
        return text
    cut = text[:200]
    # Prefer not to slice a word in half.
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return f"{cut}…"


async def _unique_slug(session: AsyncSession, desired: str, exclude_id: int | None = None) -> str:
    candidate = desired
    suffix = 2
    while True:
        stmt = select(Post.id).where(Post.slug == candidate)
        if exclude_id is not None:
            stmt = stmt.where(Post.id != exclude_id)
        existing = (await session.execute(stmt)).scalars().first()
        if existing is None:
            return candidate
        candidate = f"{desired[:150 - len(str(suffix)) - 1]}-{suffix}"
        suffix += 1


def _to_summary(post: Post) -> PostSummary:
    return PostSummary(
        id=post.id,
        slug=post.slug,
        title=post.title,
        subtitle=post.subtitle,
        excerpt=derive_excerpt(post.excerpt, post.body_markdown),
        cover_image_url=post.cover_image_url,
        status=post.status,  # type: ignore[arg-type]
        author_username=post.author.username,
        tags=sorted(t.tag for t in post.tags),
        reading_minutes=reading_minutes(post.body_markdown),
        published_at=post.published_at,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


def _to_out(post: Post) -> PostOut:
    return PostOut(**_to_summary(post).model_dump(), body_markdown=post.body_markdown)


async def _reload_out(session: AsyncSession, post_id: int) -> PostOut:
    """
    Re-select with the author eagerly loaded before serializing. Serialization
    reads post.author, and a lazy load there raises MissingGreenlet under asyncio.
    """
    stmt = select(Post).options(joinedload(Post.author)).where(Post.id == post_id)
    post = (await session.execute(stmt)).unique().scalars().first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _to_out(post)


def _apply_tags(post: Post, tags: list[str]) -> None:
    """
    Diff the tag collection rather than delete-and-reinsert: re-adding a row with
    the same primary key while the old instance is still in the identity map
    makes SQLAlchemy raise on flush.

    Only safe when post.tags is already loaded — on a freshly flushed Post the
    collection is unloaded and touching it would emit IO outside the greenlet.
    Creates pass their tags to the constructor instead.
    """
    desired = set(tags)
    current = {t.tag: t for t in post.tags}

    for tag, obj in current.items():
        if tag not in desired:
            post.tags.remove(obj)  # delete-orphan cascade removes the row
    for tag in desired:
        if tag not in current:
            post.tags.append(PostTag(post_id=post.id, tag=tag))


# ── Public reads ──────────────────────────────────────────────────────────────

@router.get("/posts", response_model=PostListOut)
async def list_posts(
    tag: str | None = Query(default=None, max_length=32),
    q: str | None = Query(default=None, max_length=100),
    include_drafts: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_session),
    current_user: User | None = Depends(get_optional_user),
) -> PostListOut:
    show_drafts = include_drafts and current_user is not None and current_user.is_mod

    filters = []
    if not show_drafts:
        filters.append(Post.status == "published")
    if tag:
        filters.append(Post.id.in_(select(PostTag.post_id).where(PostTag.tag == tag.strip().lower())))
    if q:
        needle = f"%{q.strip().lower()}%"
        filters.append(
            func.lower(Post.title).like(needle) | func.lower(Post.body_markdown).like(needle)
        )

    total = (await session.execute(select(func.count()).select_from(Post).where(*filters))).scalar_one()

    stmt = (
        select(Post)
        .options(joinedload(Post.author))
        .where(*filters)
        .order_by(
            func.coalesce(Post.published_at, Post.created_at).desc(),
            Post.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    posts = (await session.execute(stmt)).unique().scalars().all()

    return PostListOut(posts=[_to_summary(p) for p in posts], total=total)


@router.get("/posts/tags", response_model=list[TagCountOut])
async def list_tags(session: AsyncSession = Depends(db_session)) -> list[TagCountOut]:
    stmt = (
        select(PostTag.tag, func.count().label("count"))
        .join(Post, Post.id == PostTag.post_id)
        .where(Post.status == "published")
        .group_by(PostTag.tag)
        .order_by(func.count().desc(), PostTag.tag)
    )
    rows = (await session.execute(stmt)).all()
    return [TagCountOut(tag=row.tag, count=row.count) for row in rows]


@router.get("/posts/{slug}", response_model=PostOut)
async def get_post(
    slug: str,
    session: AsyncSession = Depends(db_session),
    current_user: User | None = Depends(get_optional_user),
) -> PostOut:
    stmt = select(Post).options(joinedload(Post.author)).where(Post.slug == slug)
    post = (await session.execute(stmt)).unique().scalars().first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status != "published" and not (current_user and current_user.is_mod):
        raise HTTPException(status_code=404, detail="Post not found")
    return _to_out(post)


# ── Mod writes ────────────────────────────────────────────────────────────────

@router.post("/posts", response_model=PostOut, status_code=201)
async def create_post(
    payload: PostIn,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> PostOut:
    _require_mod(current_user)

    slug = await _unique_slug(session, payload.slug or slugify(payload.title))
    post = Post(
        slug=slug,
        title=payload.title,
        subtitle=payload.subtitle,
        excerpt=payload.excerpt,
        body_markdown=payload.body_markdown,
        cover_image_url=payload.cover_image_url,
        status=payload.status,
        author_id=current_user.id,
        published_at=datetime.now(timezone.utc) if payload.status == "published" else None,
        tags=[PostTag(tag=tag) for tag in payload.tags],
    )
    session.add(post)
    await session.commit()
    return await _reload_out(session, post.id)


@router.put("/posts/{post_id}", response_model=PostOut)
async def update_post(
    post_id: int,
    payload: PostIn,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> PostOut:
    _require_mod(current_user)

    post = (await session.execute(select(Post).where(Post.id == post_id))).scalars().first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    desired_slug = payload.slug or slugify(payload.title)
    if desired_slug != post.slug:
        post.slug = await _unique_slug(session, desired_slug, exclude_id=post.id)

    post.title = payload.title
    post.subtitle = payload.subtitle
    post.excerpt = payload.excerpt
    post.body_markdown = payload.body_markdown
    post.cover_image_url = payload.cover_image_url

    # First publish stamps published_at; later edits keep the original date.
    if payload.status == "published" and post.published_at is None:
        post.published_at = datetime.now(timezone.utc)
    post.status = payload.status

    _apply_tags(post, payload.tags)
    await session.commit()
    return await _reload_out(session, post.id)


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    _require_mod(current_user)

    post = (await session.execute(select(Post).where(Post.id == post_id))).scalars().first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # delete-orphan cascade on Post.tags clears post_tag rows too.
    await session.delete(post)
    await session.commit()
