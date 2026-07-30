import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "../ui/page-header";
import { PostCard } from "../ui/post-card";
import { ModLink } from "../ui/mod-link";
import { fetchPosts, fetchTags, type PostSummary, type TagCount } from "../lib/posts";

export const metadata: Metadata = {
  title: "Archive",
  description: "Every post — analysis on the NFL draft, positional value, and the season.",
};

// Rendered per-request: the API isn't reachable at build time.
export const dynamic = "force-dynamic";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ tag?: string }>;
}) {
  const { tag } = await searchParams;

  let posts: PostSummary[] = [];
  let tags: TagCount[] = [];
  let loadError = false;

  try {
    const [list, tagList] = await Promise.all([
      fetchPosts({ tag, limit: 30 }),
      fetchTags(),
    ]);
    posts = list.posts;
    tags = tagList;
  } catch {
    loadError = true;
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:py-10">
      <PageHeader
        eyebrow="Archive"
        title="All posts"
        subtitle="Everything written, newest first. Filter by tag to narrow it down."
      >
        <ModLink href="/admin/posts" label="Manage posts" />
      </PageHeader>

      {tags.length > 0 && (
        <div className="mb-8 flex flex-wrap gap-2">
          <Link
            href="/blog"
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              !tag
                ? "border-slate-600 bg-slate-800 text-slate-100"
                : "border-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            All
          </Link>
          {tags.map((t) => (
            <Link
              key={t.tag}
              href={`/blog?tag=${encodeURIComponent(t.tag)}`}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                tag === t.tag
                  ? "border-slate-600 bg-slate-800 text-slate-100"
                  : "border-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {t.tag}
              <span className="ml-1.5 text-slate-600">{t.count}</span>
            </Link>
          ))}
        </div>
      )}

      {loadError ? (
        <div className="rounded-2xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          Couldn&apos;t reach the API. Try again in a moment.
        </div>
      ) : posts.length === 0 ? (
        <p className="text-sm text-slate-500">
          {tag ? `No posts tagged "${tag}" yet.` : "No posts yet."}
        </p>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </div>
  );
}
