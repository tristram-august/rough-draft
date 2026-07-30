export function PageHeader({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-400/80">
            {eyebrow}
          </p>
        )}
        <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">{title}</h1>
        {subtitle && (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">{subtitle}</p>
        )}
      </div>
      {children}
    </div>
  );
}
