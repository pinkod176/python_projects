import type { ReactNode } from "react";

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div role="status" className="mat mx-auto max-w-xl px-6 py-14 text-center">
      <h2 className="text-2xl md:text-3xl">{title}</h2>
      {children && <p className="mt-3 text-ink-soft">{children}</p>}
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}
