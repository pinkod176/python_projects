"use client";

import type { Facets } from "@/lib/catalog/query";
import type { UiParams } from "@/lib/catalog/params";
import { formatMoney } from "@/lib/format";

type Props = { facets: Facets; params: UiParams; onChange: (patch: Partial<UiParams>) => void; onReset: () => void; dirty: boolean };

const symbol = (c: string) => ({ RUB: "₽", RUR: "₽", USD: "$", EUR: "€" })[c.toUpperCase()] ?? c;

const check = "size-[1.15rem] shrink-0 accent-moss";
const row = "flex min-h-11 cursor-pointer items-center justify-between gap-3 transition-colors hover:text-wood";

/** Панель фильтров (цена, наличие, характеристики). Показывает только те группы, для которых в данных есть выбор. */
export function Filters({ facets, params, onChange, onReset, dirty }: Props) {
  const toggleAttr = (pair: string) =>
    onChange({ attrs: params.attrs.includes(pair) ? params.attrs.filter((a) => a !== pair) : [...params.attrs, pair] });

  return (
    <div className="space-y-8">
      {facets.price && (
        <fieldset>
          <legend className="eyebrow mb-3">Цена, {symbol(facets.price.currency)}</legend>
          <div className="flex items-center gap-2">
            <label className="min-w-0 flex-1">
              <span className="sr-only">Цена от</span>
              <input
                inputMode="numeric"
                className="field !min-h-12"
                placeholder="от"
                value={params.min}
                onChange={(e) => onChange({ min: e.target.value.replace(/[^\d]/g, "") })}
              />
            </label>
            <span aria-hidden className="text-copper">—</span>
            <label className="min-w-0 flex-1">
              <span className="sr-only">Цена до</span>
              <input
                inputMode="numeric"
                className="field !min-h-12"
                placeholder="до"
                value={params.max}
                onChange={(e) => onChange({ max: e.target.value.replace(/[^\d]/g, "") })}
              />
            </label>
          </div>
          <p className="mt-2 text-xs text-ink-soft">
            В каталоге: {formatMoney({ amount: facets.price.min, currency: facets.price.currency })} — {formatMoney({ amount: facets.price.max, currency: facets.price.currency })}
          </p>
        </fieldset>
      )}

      {facets.hasAvailabilityData && (
        <label className={row}>
          <span className="flex items-center gap-3">
            <input type="checkbox" className={check} checked={params.inStock} onChange={(e) => onChange({ inStock: e.target.checked })} />
            Только в наличии
          </span>
        </label>
      )}

      {facets.attributes.map((a) => (
        <fieldset key={a.name}>
          <legend className="eyebrow mb-3">{a.name}</legend>
          <ul>
            {a.values.map((v) => {
              const pair = `${a.name}:${v.value}`;
              return (
                <li key={pair}>
                  <label className={row}>
                    <span className="flex items-center gap-3">
                      <input type="checkbox" className={check} checked={params.attrs.includes(pair)} onChange={() => toggleAttr(pair)} />
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
        <button type="button" onClick={onReset} className="u-link min-h-11 text-sm">
          Сбросить фильтры
        </button>
      )}
    </div>
  );
}
