"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../contexts/auth-context";
import { fetchPostLike, togglePostLike } from "../lib/post-social";

export function PostLikeButton({ postId }: { postId: number }) {
  const { token } = useAuth();
  const qc = useQueryClient();
  const key = ["post-like", postId, token ?? null];

  const likeQuery = useQuery({
    queryKey: key,
    queryFn: () => fetchPostLike(postId, token),
  });

  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleToggle() {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await togglePostLike(postId, token);
      qc.invalidateQueries({ queryKey: key });
    } catch (err: any) {
      setError(err.message ?? "Failed to update like");
    } finally {
      setSubmitting(false);
    }
  }

  const likes = likeQuery.data?.likes ?? 0;
  const yourLiked = likeQuery.data?.your_liked ?? false;

  return (
    <span className="inline-flex items-center gap-1">
      <button
        type="button"
        onClick={handleToggle}
        disabled={submitting}
        className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs transition-colors disabled:opacity-50 ${
          yourLiked
            ? "border-rose-700/60 bg-rose-950/30 text-rose-400"
            : "border-slate-800 text-slate-500 hover:border-slate-700 hover:text-slate-300"
        }`}
      >
        <span aria-hidden>{yourLiked ? "♥" : "♡"}</span>
        <span>{likes}</span>
      </button>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </span>
  );
}
