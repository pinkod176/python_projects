"use client";

import type { Facets } from "@/lib/catalog/query";

type Props = { categories: Facets["categories"]; value: string; onChange: (id: string) => void };

/**
 * Подборки в виде «таблеток». Под капотом — настоящие radio-кнопки: с клавиатуры переключаются стрелками,
 * экранные читалки видят группу «Подборка». На телефоне ряд листается пальцем (полоса прокрутки скрыта),
 * выбранная таблетка плавно доезжает до видимой части.
 */
export function CategoryPills({ categories, value, onChange }: Props) {
  if (!categories.length) return null;
  const all = [{ id: "", title: "Все работы", count: undefined as number | undefined }, ...categories];
  return (
    <fieldset className="min-w-0 border-0 p-0">
      <legend className="sr-only">Подборка</legend>
      <div className="pills no-scrollbar">
        {all.map((c) => (
          <label key={c.id || "all"} className="shrink-0">
            <input
              type="radio"
              name="category"
              className="sr-only"
              checked={value === c.id}
              onChange={(e) => {
                onChange(c.id);
                e.currentTarget.closest("label")?.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
              }}
            />
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
