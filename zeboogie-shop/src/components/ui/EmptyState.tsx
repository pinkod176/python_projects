import type { ReactNode } from "react";

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div role="status" className="mat reveal-load mx-auto max-w-xl !p-0">
      <div className="rounded-sm border border-line/70 px-6 py-14 text-center md:px-10">
        <h2 className="text-h3">{title}</h2>
        {children && <p className="mx-auto mt-3 max-w-md text-ink-soft">{children}</p>}
        {action && <div className="mt-8 flex justify-center">{action}</div>}
      </div>
    </div>
  );
}
