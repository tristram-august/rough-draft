import { getClientId } from "../ui/lib/clientId";
import { API_BASE } from "./posts";
import { extractError } from "./extract-error";

export type PostComment = {
  id: number;
  post_id: number;
  user_id: number;
  username: string;
  body: string;
  created_at: string;
  updated_at: string;
};

export type PostLikeStatus = { likes: number; your_liked: boolean };

/** Identity header — anonymous likes key off the same client id as votes/picks. */
function socialHeaders(token?: string | null): HeadersInit {
  const headers: Record<string, string> = { "X-Client-Id": getClientId() };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export async function fetchPostComments(postId: number): Promise<PostComment[]> {
  const res = await fetch(`${API_BASE}/posts/${postId}/comments`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load comments (${res.status})`);
  return res.json();
}

export async function postPostComment(
  postId: number,
  body: string,
  token: string
): Promise<PostComment> {
  const res = await fetch(`${API_BASE}/posts/${postId}/comments`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(extractError(data, "Failed to post comment"));
  }
  return res.json();
}

export async function deletePostComment(commentId: number, token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/post-comments/${commentId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(extractError(data, "Failed to delete comment"));
  }
}

export async function fetchPostLike(postId: number, token?: string | null): Promise<PostLikeStatus> {
  const res = await fetch(`${API_BASE}/posts/${postId}/like`, {
    cache: "no-store",
    headers: socialHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to load like status (${res.status})`);
  return res.json();
}

export async function togglePostLike(postId: number, token?: string | null): Promise<PostLikeStatus> {
  const res = await fetch(`${API_BASE}/posts/${postId}/like`, {
    method: "POST",
    headers: socialHeaders(token),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(extractError(data, "Failed to update like"));
  }
  return res.json();
}
