import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

/**
 * No `rehype-raw` here on purpose — raw HTML in post bodies stays inert,
 * so a compromised mod account can't inject script into the page.
 */
const components: Components = {
  h1: ({ children }) => (
    <h2 className="mt-10 mb-3 text-2xl font-bold tracking-tight text-slate-100">{children}</h2>
  ),
  h2: ({ children }) => (
    <h2 className="mt-10 mb-3 text-xl font-bold tracking-tight text-slate-100">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-8 mb-2 text-lg font-semibold text-slate-100">{children}</h3>
  ),
  p: ({ children }) => (
    <p className="my-4 leading-7 text-slate-300">{children}</p>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-sky-400 underline decoration-sky-400/30 underline-offset-2 transition-colors hover:text-sky-300"
      {...(href?.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {children}
    </a>
  ),
  ul: ({ children }) => (
    <ul className="my-4 list-disc space-y-1.5 pl-6 text-slate-300 marker:text-slate-600">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-4 list-decimal space-y-1.5 pl-6 text-slate-300 marker:text-slate-600">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-7">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-6 border-l-2 border-sky-500/50 pl-4 text-slate-400 italic">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-10 border-slate-800" />,
  strong: ({ children }) => <strong className="font-semibold text-slate-100">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  code: ({ className, children }) => {
    const isBlock = Boolean(className?.startsWith("language-"));
    if (isBlock) {
      return <code className="block font-mono text-[13px] leading-relaxed">{children}</code>;
    }
    return (
      <code className="rounded-md border border-slate-800 bg-slate-900 px-1.5 py-0.5 font-mono text-[13px] text-sky-300">
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="my-5 overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/70 p-4 text-slate-300">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="my-6 overflow-x-auto rounded-2xl border border-slate-800">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-slate-900/60">{children}</thead>,
  th: ({ children }) => (
    <th className="border-b border-slate-800 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-slate-800/60 px-3 py-2 text-slate-300">{children}</td>
  ),
  img: ({ src, alt }) =>
    typeof src === "string" ? (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={src} alt={alt ?? ""} className="my-6 w-full rounded-2xl border border-slate-800" />
    ) : null,
};

export function MarkdownBody({ children }: { children: string }) {
  return (
    <div className="text-[15px] sm:text-base">
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </Markdown>
    </div>
  );
}
