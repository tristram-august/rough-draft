"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../contexts/auth-context";
import { deletePostComment, fetchPostComments, postPostComment } from "../lib/post-social";

export function PostComments({ postId }: { postId: number }) {
  const { user, token } = useAuth();
  const qc = useQueryClient();
  const commentsKey = ["post-comments", postId];

  const commentsQuery = useQuery({
    queryKey: commentsKey,
    queryFn: () => fetchPostComments(postId),
  });

  const [body, setBody] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  async function handlePost(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token || !body.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await postPostComment(postId, body.trim(), token);
      setBody("");
      qc.invalidateQueries({ queryKey: commentsKey });
    } catch (err: any) {
      setSubmitError(err.message ?? "Failed to post");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(commentId: number) {
    if (!token) return;
    try {
      await deletePostComment(commentId, token);
      qc.invalidateQueries({ queryKey: commentsKey });
    } catch {
      // silently ignore
    }
  }

  const comments = commentsQuery.data ?? [];

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5 space-y-4">
      <div className="text-xs text-slate-500">Comments</div>

      {commentsQuery.isLoading ? (
        <div className="text-xs text-slate-500">Loading…</div>
      ) : comments.length === 0 ? (
        <div className="text-xs text-slate-500">No comments yet — be the first!</div>
      ) : (
        <div className="space-y-2">
          {comments.map((c) => (
            <div key={c.id} className="rounded-2xl border border-slate-800 bg-slate-950/30 px-4 py-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <Link href={`/profile/${c.username}`} className="text-xs font-medium text-slate-300 hover:text-slate-100 transition-colors">
                  {c.username}
                </Link>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-600">
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                  {(user?.user_id === c.user_id || user?.is_mod) && (
                    <button
                      type="button"
                      onClick={() => handleDelete(c.id)}
                      className="text-[10px] text-slate-600 hover:text-red-400 transition-colors"
                    >
                      delete
                    </button>
                  )}
                </div>
              </div>
              <div className="text-sm text-slate-200 whitespace-pre-wrap">{c.body}</div>
            </div>
          ))}
        </div>
      )}

      {user ? (
        <form onSubmit={handlePost} className="space-y-2">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Share your take…"
            rows={3}
            className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-slate-500 resize-none"
          />
          {submitError && (
            <div className="text-xs text-red-400">{submitError}</div>
          )}
          <button
            type="submit"
            disabled={submitting || !body.trim()}
            className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-2 text-xs text-slate-100 hover:bg-slate-700 disabled:opacity-40 transition-colors"
          >
            {submitting ? "Posting…" : "Post comment"}
          </button>
        </form>
      ) : (
        <div className="text-xs text-slate-500">
          Sign in to leave a comment.
        </div>
      )}
    </div>
  );
}
