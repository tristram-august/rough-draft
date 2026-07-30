"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../contexts/auth-context";
import { fetchPosts, formatPostDate } from "../../lib/posts";

export default function Page() {
  const { user, token } = useAuth();

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-posts", token],
    queryFn: () => fetchPosts({ includeDrafts: true, limit: 50, token }),
    enabled: Boolean(token && user?.is_mod),
  });

  if (!user) {
    return <p className="text-sm text-slate-400">Sign in to manage posts.</p>;
  }
  if (!user.is_mod) {
    return <p className="text-sm text-slate-400">Post management is limited to mods.</p>;
  }

  const posts = data?.posts ?? [];

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Posts</h1>
          <p className="mt-1 text-sm text-slate-500">
            {data ? `${data.total} total` : " "}
          </p>
        </div>
        <Link
          href="/admin/posts/new"
          className="rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 transition-colors hover:bg-slate-700"
        >
          New post
        </Link>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {error && (
        <div className="rounded-xl border border-red-800/40 bg-red-950/20 px-3 py-2 text-sm text-red-300">
          {error instanceof Error ? error.message : "Couldn't load posts"}
        </div>
      )}

      {data && posts.length === 0 && (
        <p className="text-sm text-slate-500">
          No posts yet.{" "}
          <Link href="/admin/posts/new" className="text-sky-400 hover:text-sky-300">
            Write the first one.
          </Link>
        </p>
      )}

      <div className="divide-y divide-slate-800/70">
        {posts.map((post) => (
          <div key={post.id} className="flex flex-wrap items-center gap-3 py-3">
            <span
              className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                post.status === "published"
                  ? "border-emerald-800/60 bg-emerald-950/30 text-emerald-400"
                  : "border-amber-700/50 bg-amber-950/30 text-amber-400"
              }`}
            >
              {post.status}
            </span>

            <div className="min-w-0 flex-1">
              <Link
                href={`/admin/posts/${post.slug}`}
                className="block truncate text-sm font-medium text-slate-100 transition-colors hover:text-sky-300"
              >
                {post.title}
              </Link>
              <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
                <span>{formatPostDate(post.published_at ?? post.created_at)}</span>
                <span aria-hidden>·</span>
                <span>{post.reading_minutes} min</span>
                {post.tags.length > 0 && (
                  <>
                    <span aria-hidden>·</span>
                    <span className="truncate">{post.tags.join(", ")}</span>
                  </>
                )}
              </div>
            </div>

            <div className="flex shrink-0 gap-3 text-xs">
              <Link
                href={`/admin/posts/${post.slug}`}
                className="text-slate-400 transition-colors hover:text-slate-200"
              >
                Edit
              </Link>
              <Link
                href={`/blog/${post.slug}`}
                className="text-slate-400 transition-colors hover:text-slate-200"
              >
                View
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
