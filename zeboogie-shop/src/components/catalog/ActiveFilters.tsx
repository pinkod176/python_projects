"use client";

import { X } from "lucide-react";
import type { UiParams } from "@/lib/catalog/params";
import type { Facets } from "@/lib/catalog/query";

type Props = { facets: Facets; params: UiParams; onChange: (patch: Partial<UiParams>) => void; onResetAll: () => void };

/** Выбранные фильтры в виде чипов с крестиком + «Сбросить всё». Каждый чип — настоящая кнопка с понятным названием. */
export function ActiveFilters({ facets, params, onChange, onResetAll }: Props) {
  const chips: { key: string; label: string; remove: () => void }[] = [];
  if (params.q.trim()) chips.push({ key: "q", label: `Поиск: «${params.q.trim()}»`, remove: () => onChange({ q: "" }) });
  const cat = facets.categories.find((c) => c.id === params.category);
  if (cat) chips.push({ key: "cat", label: cat.title, remove: () => onChange({ category: "" }) });
  if (params.min || params.max) {
    const fmt = (v: string) => Number(v).toLocaleString("ru-RU");
    const label = params.min && params.max ? `${fmt(params.min)} – ${fmt(params.max)} ₽` : params.min ? `от ${fmt(params.min)} ₽` : `до ${fmt(params.max)} ₽`;
    chips.push({ key: "price", label, remove: () => onChange({ min: "", max: "" }) });
  }
  if (params.inStock) chips.push({ key: "stock", label: "В наличии", remove: () => onChange({ inStock: false }) });
  for (const pair of params.attrs) {
    const i = pair.indexOf(":");
    chips.push({ key: pair, label: `${pair.slice(0, i)}: ${pair.slice(i + 1)}`, remove: () => onChange({ attrs: params.attrs.filter((a) => a !== pair) }) });
  }
  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Выбранные фильтры">
      {chips.map((c) => (
        <button key={c.key} type="button" className="chip chip-x" onClick={c.remove} aria-label={`Убрать фильтр: ${c.label}`}>
          {c.label}
          <X aria-hidden className="size-4 text-ink-soft" strokeWidth={1.75} />
        </button>
      ))}
      <button type="button" className="u-link ml-1 min-h-11 text-sm" onClick={onResetAll}>
        Сбросить всё
      </button>
    </div>
  );
}
