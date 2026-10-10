import Link from "next/link";

export type Crumb = { label: string; href?: string };

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Хлебные крошки" className="text-sm text-ink-soft">
      <ol className="flex flex-wrap items-center gap-x-2.5">
        {items.map((c, i) => (
          <li key={i} className="flex min-h-11 items-center gap-2.5">
            {i > 0 && <span aria-hidden className="text-copper">/</span>}
            {c.href ? (
              <Link href={c.href} className="u-link inline-flex min-h-11 items-center">
                {c.label}
              </Link>
            ) : (
              <span aria-current="page" className="text-ink">
                {c.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
