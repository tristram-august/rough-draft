export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export type PostStatus = "draft" | "published";

export type PostSummary = {
  id: number;
  slug: string;
  title: string;
  subtitle: string | null;
  excerpt: string | null;
  cover_image_url: string | null;
  status: PostStatus;
  author_username: string;
  tags: string[];
  reading_minutes: number;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  like_count: number;
  comment_count: number;
};

export type Post = PostSummary & { body_markdown: string };

export type PostListResponse = { posts: PostSummary[]; total: number };

export type TagCount = { tag: string; count: number };

/** Payload accepted by POST /posts and PUT /posts/{id}. */
export type PostInput = {
  title: string;
  slug?: string | null;
  subtitle?: string | null;
  excerpt?: string | null;
  body_markdown: string;
  cover_image_url?: string | null;
  status: PostStatus;
  tags: string[];
};

type ListParams = {
  tag?: string;
  q?: string;
  limit?: number;
  offset?: number;
  includeDrafts?: boolean;
  token?: string | null;
};

function authHeaders(token?: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchPosts({
  tag,
  q,
  limit = 20,
  offset = 0,
  includeDrafts = false,
  token,
}: ListParams = {}): Promise<PostListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (tag) params.set("tag", tag);
  if (q) params.set("q", q);
  if (includeDrafts) params.set("include_drafts", "true");

  const res = await fetch(`${API_BASE}/posts?${params}`, {
    cache: "no-store",
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to load posts (${res.status})`);
  return res.json();
}

/** Returns null on 404 so callers can render notFound() themselves. */
export async function fetchPost(slug: string, token?: string | null): Promise<Post | null> {
  const res = await fetch(`${API_BASE}/posts/${encodeURIComponent(slug)}`, {
    cache: "no-store",
    headers: authHeaders(token),
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load post (${res.status})`);
  return res.json();
}

export async function fetchTags(): Promise<TagCount[]> {
  const res = await fetch(`${API_BASE}/posts/tags`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export function formatPostDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}
