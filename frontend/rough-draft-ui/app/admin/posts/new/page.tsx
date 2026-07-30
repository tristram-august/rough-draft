import Link from "next/link";
import { PostEditor } from "../../../ui/post-editor";

export default function Page() {
  return (
    <div>
      <Link
        href="/admin/posts"
        className="text-xs font-medium text-slate-500 transition-colors hover:text-slate-300"
      >
        <span aria-hidden>←</span> All posts
      </Link>
      <h1 className="mt-4 mb-6 text-2xl font-bold tracking-tight">New post</h1>
      <PostEditor />
    </div>
  );
}
