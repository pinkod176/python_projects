"use client";

import type { Facets } from "@/lib/catalog/query";

type Props = { categories: Facets["categories"]; value: string; onChange: (id: string) => void };

/**
 * Подборки в виде спокойных «таблеток». Под капотом — обычные radio-кнопки (доступны с клавиатуры и экранным читалкам),
 * на телефоне ряд прокручивается по горизонтали.
 */
export function CategoryPills({ categories, value, onChange }: Props) {
  if (!categories.length) return null;
  const all = [{ id: "", title: "Все работы", count: undefined as number | undefined }, ...categories];
  return (
    <fieldset className="min-w-0">
      <legend className="sr-only">Подборка</legend>
      <div className="no-scrollbar relative -mx-[var(--gutter)] flex gap-2 overflow-x-auto px-[var(--gutter)] py-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0">
        {all.map((c) => (
          <label key={c.id || "all"} className="shrink-0">
            <input type="radio" name="category" className="sr-only" checked={value === c.id} onChange={() => onChange(c.id)} />
            <span className="chip">
              {c.title}
              {c.count !== undefined && <small>{c.count}</small>}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
