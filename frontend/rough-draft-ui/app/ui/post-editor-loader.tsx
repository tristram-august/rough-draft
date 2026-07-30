"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../contexts/auth-context";
import { fetchPost } from "../lib/posts";
import { PostEditor } from "./post-editor";

/**
 * Drafts are only readable with a mod token, so the existing post has to be
 * fetched client-side rather than in the server component above.
 */
export function PostEditorLoader({ slug }: { slug: string }) {
  const { user, token } = useAuth();

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-post", slug, token],
    queryFn: () => fetchPost(slug, token),
    enabled: Boolean(token && user?.is_mod),
  });

  if (!user) return <p className="text-sm text-slate-400">Sign in to edit posts.</p>;
  if (!user.is_mod) return <p className="text-sm text-slate-400">Post editing is limited to mods.</p>;
  if (isLoading) return <p className="text-sm text-slate-500">Loading…</p>;
  if (error) {
    return (
      <div className="rounded-xl border border-red-800/40 bg-red-950/20 px-3 py-2 text-sm text-red-300">
        {error instanceof Error ? error.message : "Couldn't load the post"}
      </div>
    );
  }
  if (!data) return <p className="text-sm text-slate-400">That post doesn&apos;t exist.</p>;

  return <PostEditor existing={data} />;
}
