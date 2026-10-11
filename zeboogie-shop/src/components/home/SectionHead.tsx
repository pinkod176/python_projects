import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";
import { Reveal } from "@/components/ui/Reveal";

export function SectionHead({ eyebrow, title, titleId, href, linkLabel, children }: { eyebrow?: string; title: ReactNode; titleId?: string; href?: string; linkLabel?: string; children?: ReactNode }) {
  return (
    <Reveal className="mb-8 flex flex-wrap items-end justify-between gap-x-6 gap-y-3 md:mb-12">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2 id={titleId} className="mt-3 text-h2 font-light">{title}</h2>
        {children && <p className="mt-4 max-w-lg text-ink-soft">{children}</p>}
      </div>
      {href && (
        <Link href={href} className="u-link inline-flex min-h-11 items-center gap-2 text-sm">
          {linkLabel ?? "Смотреть все"} <ArrowRight aria-hidden className="size-4" />
        </Link>
      )}
    </Reveal>
  );
}
