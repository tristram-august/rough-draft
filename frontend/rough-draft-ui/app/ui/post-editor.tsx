"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "../contexts/auth-context";
import { extractError } from "../lib/extract-error";
import { MarkdownBody } from "./markdown";
import { API_BASE, type Post, type PostStatus } from "../lib/posts";

/** Mirrors the backend's slugify so the previewed URL matches what gets saved. */
function slugify(title: string) {
  return title
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 150);
}

type ToolbarAction =
  | { kind: "wrap"; label: string; title: string; before: string; after: string }
  | { kind: "prefix"; label: string; title: string; prefix: string };

const TOOLBAR: ToolbarAction[] = [
  { kind: "wrap", label: "B", title: "Bold", before: "**", after: "**" },
  { kind: "wrap", label: "I", title: "Italic", before: "_", after: "_" },
  { kind: "prefix", label: "H2", title: "Heading", prefix: "## " },
  { kind: "wrap", label: "Link", title: "Link", before: "[", after: "](https://)" },
  { kind: "prefix", label: "List", title: "Bulleted list", prefix: "- " },
  { kind: "prefix", label: "Quote", title: "Blockquote", prefix: "> " },
  { kind: "wrap", label: "Code", title: "Inline code", before: "`", after: "`" },
];

export function PostEditor({ existing }: { existing?: Post }) {
  const { user, token } = useAuth();
  const router = useRouter();

  const [title, setTitle] = React.useState(existing?.title ?? "");
  const [subtitle, setSubtitle] = React.useState(existing?.subtitle ?? "");
  const [slug, setSlug] = React.useState(existing?.slug ?? "");
  const [slugEdited, setSlugEdited] = React.useState(Boolean(existing));
  const [excerpt, setExcerpt] = React.useState(existing?.excerpt ?? "");
  const [coverImage, setCoverImage] = React.useState(existing?.cover_image_url ?? "");
  const [tagsText, setTagsText] = React.useState((existing?.tags ?? []).join(", "));
  const [body, setBody] = React.useState(existing?.body_markdown ?? "");

  const [tab, setTab] = React.useState<"write" | "preview">("write");
  const [error, setError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState<PostStatus | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  const bodyRef = React.useRef<HTMLTextAreaElement>(null);
  const effectiveSlug = slugEdited && slug ? slug : slugify(title);

  function applyAction(action: ToolbarAction) {
    const el = bodyRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;

    if (action.kind === "wrap") {
      const selected = body.slice(start, end);
      const next = body.slice(0, start) + action.before + selected + action.after + body.slice(end);
      setBody(next);
      const caret = start + action.before.length;
      requestAnimationFrame(() => {
        el.focus();
        el.setSelectionRange(caret, caret + selected.length);
      });
      return;
    }

    // Prefix every line the selection touches.
    const lineStart = body.lastIndexOf("\n", start - 1) + 1;
    const lineEndIdx = body.indexOf("\n", end);
    const lineEnd = lineEndIdx === -1 ? body.length : lineEndIdx;
    const block = body.slice(lineStart, lineEnd);
    const prefixed = block
      .split("\n")
      .map((line) => (line.startsWith(action.prefix) ? line : action.prefix + line))
      .join("\n");
    setBody(body.slice(0, lineStart) + prefixed + body.slice(lineEnd));
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(lineStart, lineStart + prefixed.length);
    });
  }

  async function save(status: PostStatus) {
    setError(null);

    if (!title.trim()) {
      setError("A title is required.");
      return;
    }
    setSaving(status);

    const payload = {
      title: title.trim(),
      slug: effectiveSlug || null,
      subtitle: subtitle.trim() || null,
      excerpt: excerpt.trim() || null,
      cover_image_url: coverImage.trim() || null,
      body_markdown: body,
      status,
      tags: tagsText
        .split(",")
        .map((t) => t.trim().toLowerCase())
        .filter(Boolean),
    };

    try {
      const res = await fetch(
        existing ? `${API_BASE}/posts/${existing.id}` : `${API_BASE}/posts`,
        {
          method: existing ? "PUT" : "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(extractError(data, "Couldn't save the post"));
      }
      const saved: Post = await res.json();
      router.push(status === "published" ? `/blog/${saved.slug}` : "/admin/posts");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save the post");
    } finally {
      setSaving(null);
    }
  }

  async function handleDelete() {
    if (!existing) return;
    if (!window.confirm(`Delete "${existing.title}"? This can't be undone.`)) return;

    setDeleting(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/posts/${existing.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(extractError(data, "Couldn't delete the post"));
      }
      router.push("/admin/posts");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't delete the post");
      setDeleting(false);
    }
  }

  if (!user) {
    return <p className="text-sm text-slate-400">Sign in to write posts.</p>;
  }
  if (!user.is_mod) {
    return <p className="text-sm text-slate-400">Post editing is limited to mods.</p>;
  }

  const inputClass =
    "w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none transition-colors focus:border-slate-500 placeholder:text-slate-600";
  const labelClass = "text-xs font-medium text-slate-500";

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className={labelClass}>Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Why the 2016 QB class fell apart"
            className={`${inputClass} mt-1 text-base font-medium`}
          />
        </div>

        <div className="sm:col-span-2">
          <label className={labelClass}>Subtitle</label>
          <input
            value={subtitle}
            onChange={(e) => setSubtitle(e.target.value)}
            placeholder="Optional deck under the headline"
            className={`${inputClass} mt-1`}
          />
        </div>

        <div>
          <label className={labelClass}>
            URL slug <span className="text-slate-600">/blog/{effectiveSlug || "…"}</span>
          </label>
          <input
            value={slugEdited ? slug : slugify(title)}
            onChange={(e) => {
              setSlugEdited(true);
              setSlug(e.target.value);
            }}
            placeholder="auto-generated from the title"
            className={`${inputClass} mt-1 font-mono text-xs`}
          />
        </div>

        <div>
          <label className={labelClass}>Tags (comma separated)</label>
          <input
            value={tagsText}
            onChange={(e) => setTagsText(e.target.value)}
            placeholder="draft, fantasy, quarterbacks"
            className={`${inputClass} mt-1`}
          />
        </div>

        <div className="sm:col-span-2">
          <label className={labelClass}>Cover image URL</label>
          <input
            value={coverImage}
            onChange={(e) => setCoverImage(e.target.value)}
            placeholder="https://…"
            className={`${inputClass} mt-1 font-mono text-xs`}
          />
        </div>

        <div className="sm:col-span-2">
          <label className={labelClass}>
            Excerpt <span className="text-slate-600">— leave blank to pull from the body</span>
          </label>
          <textarea
            value={excerpt}
            onChange={(e) => setExcerpt(e.target.value)}
            rows={2}
            placeholder="Shown on the blog index and in link previews"
            className={`${inputClass} mt-1 resize-y`}
          />
        </div>
      </div>

      {/* Body: write / preview */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900/30">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 px-3 py-2">
          <div className="flex gap-1">
            {(["write", "preview"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                  tab === t
                    ? "bg-slate-800 text-slate-100"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === "write" && (
            <div className="flex flex-wrap gap-1">
              {TOOLBAR.map((action) => (
                <button
                  key={action.label}
                  type="button"
                  title={action.title}
                  onClick={() => applyAction(action)}
                  className={`rounded-md border border-slate-800 px-2 py-1 text-xs text-slate-400 transition-colors hover:border-slate-700 hover:text-slate-200 ${
                    action.label === "B" ? "font-bold" : ""
                  } ${action.label === "I" ? "italic" : ""}`}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {tab === "write" ? (
          <textarea
            ref={bodyRef}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={22}
            placeholder="Write in markdown. Headings, **bold**, lists, tables, and code fences all work."
            className="w-full resize-y bg-transparent px-4 py-4 font-mono text-[13px] leading-relaxed text-slate-200 outline-none placeholder:text-slate-600"
          />
        ) : (
          <div className="px-5 py-4">
            {body.trim() ? (
              <MarkdownBody>{body}</MarkdownBody>
            ) : (
              <p className="py-8 text-center text-sm text-slate-600">Nothing to preview yet.</p>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-800/40 bg-red-950/20 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => save("published")}
          disabled={saving !== null || deleting}
          className="rounded-xl border border-sky-700 bg-sky-900/40 px-4 py-2 text-sm font-medium text-sky-100 transition-colors hover:bg-sky-900/70 disabled:opacity-50"
        >
          {saving === "published"
            ? "Publishing…"
            : existing?.status === "published"
              ? "Update published post"
              : "Publish"}
        </button>
        <button
          type="button"
          onClick={() => save("draft")}
          disabled={saving !== null || deleting}
          className="rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 transition-colors hover:bg-slate-700 disabled:opacity-50"
        >
          {saving === "draft" ? "Saving…" : existing?.status === "published" ? "Unpublish to draft" : "Save draft"}
        </button>

        <Link
          href="/admin/posts"
          className="rounded-xl border border-slate-800 px-4 py-2 text-sm text-slate-400 transition-colors hover:text-slate-200"
        >
          Cancel
        </Link>

        {existing && (
          <button
            type="button"
            onClick={handleDelete}
            disabled={saving !== null || deleting}
            className="ml-auto rounded-xl border border-red-900/50 px-4 py-2 text-sm text-red-400 transition-colors hover:bg-red-950/30 disabled:opacity-50"
          >
            {deleting ? "Deleting…" : "Delete"}
          </button>
        )}
      </div>
    </div>
  );
}
