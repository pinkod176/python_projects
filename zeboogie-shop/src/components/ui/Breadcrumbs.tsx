import Link from "next/link";

export type Crumb = { label: string; href?: string };

/**
 * Хлебные крошки. На телефоне — всегда одна строка (последняя «крошка» с многоточием), чтобы первый экран не «прыгал»
 * от длинных названий; на широких экранах переносятся.
 */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Хлебные крошки" className="text-sm text-ink-soft">
      <ol className="flex flex-nowrap items-center gap-x-2.5 md:flex-wrap">
        {items.map((c, i) => {
          const last = i === items.length - 1;
          return (
            <li key={i} className={`flex min-h-11 items-center gap-2.5 ${last ? "min-w-0" : "shrink-0"}`}>
              {i > 0 && <span aria-hidden className="text-copper">/</span>}
              {c.href ? (
                <Link href={c.href} className="u-link inline-flex min-h-11 items-center whitespace-nowrap">
                  {c.label}
                </Link>
              ) : (
                <span aria-current="page" className="min-w-0 truncate text-ink md:overflow-visible md:whitespace-normal">
                  {c.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
