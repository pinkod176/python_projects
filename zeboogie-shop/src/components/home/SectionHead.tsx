import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";

export function SectionHead({ eyebrow, title, href, linkLabel, children }: { eyebrow?: string; title: ReactNode; href?: string; linkLabel?: string; children?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4 md:mb-12">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2 className="mt-2 text-4xl md:text-5xl">{title}</h2>
        {children && <p className="mt-3 max-w-lg text-ink-soft">{children}</p>}
      </div>
      {href && (
        <Link href={href} className="inline-flex min-h-11 items-center gap-2 border-b border-ink text-sm hover:text-moss">
          {linkLabel ?? "Смотреть все"} <ArrowRight aria-hidden className="size-4" />
        </Link>
      )}
    </div>
  );
}
