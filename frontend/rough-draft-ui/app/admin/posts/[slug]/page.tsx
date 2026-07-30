import Link from "next/link";
import { PostEditorLoader } from "../../../ui/post-editor-loader";

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return (
    <div>
      <Link
        href="/admin/posts"
        className="text-xs font-medium text-slate-500 transition-colors hover:text-slate-300"
      >
        <span aria-hidden>←</span> All posts
      </Link>
      <h1 className="mt-4 mb-6 text-2xl font-bold tracking-tight">Edit post</h1>
      <PostEditorLoader slug={slug} />
    </div>
  );
}
