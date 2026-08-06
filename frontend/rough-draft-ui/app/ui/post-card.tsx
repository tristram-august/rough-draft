import Link from "next/link";
import { formatPostDate, type PostSummary } from "../lib/posts";

export function PostCard({ post }: { post: PostSummary }) {
  return (
    <article className="group rounded-3xl border border-slate-800 bg-slate-900/30 transition-colors hover:border-slate-700 hover:bg-slate-900/60">
      <Link href={`/blog/${post.slug}`} className="block p-6">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-slate-500">
          {post.status === "draft" && (
            <span className="rounded-full border border-amber-700/50 bg-amber-950/30 px-2 py-0.5 font-medium text-amber-400">
              Draft
            </span>
          )}
          <span>{formatPostDate(post.published_at ?? post.created_at)}</span>
          <span aria-hidden>·</span>
          <span>{post.reading_minutes} min read</span>
          <span aria-hidden>·</span>
          <span>{post.author_username}</span>
          <span aria-hidden>·</span>
          <span className="inline-flex items-center gap-1">
            <span aria-hidden>♡</span>
            {post.like_count}
          </span>
          <span className="inline-flex items-center gap-1">
            <span aria-hidden>💬</span>
            {post.comment_count}
          </span>
        </div>

        <h2 className="mt-2.5 text-xl font-semibold leading-snug tracking-tight text-slate-100 transition-colors group-hover:text-white">
          {post.title}
        </h2>
        {post.subtitle && (
          <p className="mt-1.5 text-sm font-medium text-slate-400">{post.subtitle}</p>
        )}
        {post.excerpt && (
          <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-slate-400">{post.excerpt}</p>
        )}

        {post.tags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {post.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-slate-800 px-2.5 py-0.5 text-xs text-slate-500"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </Link>
    </article>
  );
}
