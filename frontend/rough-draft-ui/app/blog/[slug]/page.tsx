import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MarkdownBody } from "../../ui/markdown";
import { PostComments } from "../../ui/post-comments";
import { PostLikeButton } from "../../ui/post-like-button";
import { fetchPost, formatPostDate } from "../../lib/posts";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await fetchPost(slug).catch(() => null);
  if (!post) return { title: "Post not found" };

  return {
    title: post.title,
    description: post.excerpt ?? post.subtitle ?? undefined,
    openGraph: {
      title: post.title,
      description: post.excerpt ?? post.subtitle ?? undefined,
      type: "article",
      publishedTime: post.published_at ?? undefined,
      images: post.cover_image_url ? [post.cover_image_url] : undefined,
    },
  };
}

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = await fetchPost(slug).catch(() => null);
  if (!post) notFound();

  return (
    <article className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
      <Link
        href="/blog"
        className="text-xs font-medium text-slate-500 transition-colors hover:text-slate-300"
      >
        <span aria-hidden>←</span> All posts
      </Link>

      <header className="mt-6 border-b border-slate-800 pb-8">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-slate-500">
          {post.status === "draft" && (
            <span className="rounded-full border border-amber-700/50 bg-amber-950/30 px-2 py-0.5 font-medium text-amber-400">
              Draft — only mods can see this
            </span>
          )}
          <span>{formatPostDate(post.published_at ?? post.created_at)}</span>
          <span aria-hidden>·</span>
          <span>{post.reading_minutes} min read</span>
          <span aria-hidden>·</span>
          <span>{post.author_username}</span>
          <PostLikeButton postId={post.id} />
        </div>

        <h1 className="mt-3 text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
          {post.title}
        </h1>
        {post.subtitle && (
          <p className="mt-3 text-lg leading-relaxed text-slate-400">{post.subtitle}</p>
        )}

        {post.tags.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-1.5">
            {post.tags.map((tag) => (
              <Link
                key={tag}
                href={`/blog?tag=${encodeURIComponent(tag)}`}
                className="rounded-full border border-slate-800 px-2.5 py-0.5 text-xs text-slate-500 transition-colors hover:border-slate-700 hover:text-slate-300"
              >
                {tag}
              </Link>
            ))}
          </div>
        )}
      </header>

      {post.cover_image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={post.cover_image_url}
          alt=""
          className="mx-auto mt-8 max-w-full rounded-3xl border border-slate-800"
        />
      )}

      <div className="mt-2">
        <MarkdownBody>{post.body_markdown}</MarkdownBody>
      </div>

      <div className="mt-10 border-t border-slate-800 pt-8">
        <PostComments postId={post.id} />
      </div>
    </article>
  );
}
