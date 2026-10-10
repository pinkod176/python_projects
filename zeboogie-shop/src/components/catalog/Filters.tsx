"use client";

import type { Facets } from "@/lib/catalog/query";
import type { UiParams } from "@/lib/catalog/params";

type Props = { facets: Facets; params: UiParams; onChange: (patch: Partial<UiParams>) => void; onReset: () => void; dirty: boolean };

const symbol = (c: string) => ({ RUB: "₽", RUR: "₽", USD: "$", EUR: "€" })[c.toUpperCase()] ?? c;

/** Панель фильтров. Показывает только те группы, для которых в данных есть выбор. */
export function Filters({ facets, params, onChange, onReset, dirty }: Props) {
  const toggleAttr = (pair: string) =>
    onChange({ attrs: params.attrs.includes(pair) ? params.attrs.filter((a) => a !== pair) : [...params.attrs, pair] });

  return (
    <div className="space-y-8">
      {facets.categories.length > 0 && (
        <fieldset>
          <legend className="eyebrow mb-3">Подборка</legend>
          <ul className="space-y-0.5">
            {[{ id: "", title: "Все работы", count: facets.categories.reduce((s, c) => s + c.count, 0) }, ...facets.categories].map((c) => (
              <li key={c.id || "all"}>
                <label className="flex min-h-11 cursor-pointer items-center justify-between gap-3 hover:text-moss">
                  <span className="flex items-center gap-3">
                    <input
                      type="radio"
                      name="category"
                      checked={params.category === c.id}
                      onChange={() => onChange({ category: c.id })}
                      className="size-4 accent-moss"
                    />
                    <span className={params.category === c.id ? "font-medium" : ""}>{c.title}</span>
                  </span>
                  <span className="text-xs text-ink-soft">{c.id === "" ? "" : c.count}</span>
                </label>
              </li>
            ))}
          </ul>
        </fieldset>
      )}

      {facets.price && (
        <fieldset>
          <legend className="eyebrow mb-3">Цена, {symbol(facets.price.currency)}</legend>
          <div className="flex items-center gap-2">
            <label className="flex-1">
              <span className="sr-only">Цена от</span>
              <input
                inputMode="numeric"
                className="field"
                placeholder={`от ${Math.floor(facets.price.min / 100)}`}
                value={params.min}
                onChange={(e) => onChange({ min: e.target.value.replace(/[^\d]/g, "") })}
              />
            </label>
            <span aria-hidden>—</span>
            <label className="flex-1">
              <span className="sr-only">Цена до</span>
              <input
                inputMode="numeric"
                className="field"
                placeholder={`до ${Math.ceil(facets.price.max / 100)}`}
                value={params.max}
                onChange={(e) => onChange({ max: e.target.value.replace(/[^\d]/g, "") })}
              />
            </label>
          </div>
        </fieldset>
      )}

      {facets.hasAvailabilityData && (
        <label className="flex min-h-11 cursor-pointer items-center gap-3">
          <input type="checkbox" className="size-4 accent-moss" checked={params.inStock} onChange={(e) => onChange({ inStock: e.target.checked })} />
          Только в наличии
        </label>
      )}

      {facets.attributes.map((a) => (
        <fieldset key={a.name}>
          <legend className="eyebrow mb-3">{a.name}</legend>
          <ul className="space-y-0.5">
            {a.values.map((v) => {
              const pair = `${a.name}:${v.value}`;
              return (
                <li key={pair}>
                  <label className="flex min-h-11 cursor-pointer items-center justify-between gap-3">
                    <span className="flex items-center gap-3">
                      <input type="checkbox" className="size-4 accent-moss" checked={params.attrs.includes(pair)} onChange={() => toggleAttr(pair)} />
                      {v.value}
                    </span>
                    <span className="text-xs text-ink-soft">{v.count}</span>
                  </label>
                </li>
              );
            })}
          </ul>
        </fieldset>
      ))}

      {dirty && (
        <button type="button" onClick={onReset} className="min-h-11 text-sm underline underline-offset-4 hover:text-moss">
          Сбросить фильтры
        </button>
      )}
    </div>
  );
}
