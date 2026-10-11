"use client";

import type { Facets } from "@/lib/catalog/query";
import type { UiParams } from "@/lib/catalog/params";
import { PriceRange } from "./PriceRange";

type Props = {
  facets: Facets;
  params: UiParams;
  onChange: (patch: Partial<UiParams>) => void;
  /** Показывать группу «Подборка» (в шторке на телефоне плашек-подборок над сеткой не видно). */
  withCategory?: boolean;
};

const group = "min-w-0 border-0 p-0";

/**
 * Группы фильтров: подборка, цена, формат (размер), другие характеристики, наличие.
 * Показываются только те группы, для которых в данных есть из чего выбирать: например, «Порода дерева» появится,
 * когда у работ в сообществе будет такая характеристика. Изменения применяются сразу.
 */
export function Filters({ facets, params, onChange, withCategory }: Props) {
  const toggleAttr = (pair: string) =>
    onChange({ attrs: params.attrs.includes(pair) ? params.attrs.filter((a) => a !== pair) : [...params.attrs, pair] });

  return (
    <div className="space-y-8">
      {withCategory && facets.categories.length > 0 && (
        <fieldset className={group}>
          <legend className="eyebrow mb-3">Подборка</legend>
          <div className="flex flex-wrap gap-2">
            {[{ id: "", title: "Все работы" }, ...facets.categories].map((c) => (
              <label key={c.id || "all"}>
                <input type="radio" name="filter-category" className="sr-only" checked={params.category === c.id} onChange={() => onChange({ category: c.id })} />
                <span className="chip">{c.title}</span>
              </label>
            ))}
          </div>
        </fieldset>
      )}

      {facets.price && facets.price.points.length > 1 && (
        <fieldset className={group}>
          <legend className="eyebrow mb-2">Цена, ₽</legend>
          <PriceRange price={facets.price} min={params.min} max={params.max} onChange={(next) => onChange(next)} />
        </fieldset>
      )}

      {facets.attributes.map((a) => (
        <fieldset key={a.name} className={group}>
          <legend className="eyebrow mb-3">{a.name === "Формат" ? "Формат (размер)" : a.name}</legend>
          <div className="flex flex-wrap gap-2">
            {a.values.map((v) => {
              const pair = `${a.name}:${v.value}`;
              return (
                <label key={pair}>
                  <input type="checkbox" className="sr-only" checked={params.attrs.includes(pair)} onChange={() => toggleAttr(pair)} />
                  <span className="chip">
                    {v.value}
                    <small>{v.count}</small>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>
      ))}

      {facets.hasAvailabilityData && (
        <fieldset className={group}>
          <legend className="eyebrow mb-3">Наличие</legend>
          <label className="inline-flex min-h-11 cursor-pointer items-center gap-3">
            <input type="checkbox" className="sr-only" checked={params.inStock} onChange={(e) => onChange({ inStock: e.target.checked })} />
            <span className="chip">Только в наличии</span>
          </label>
        </fieldset>
      )}
    </div>
  );
}
