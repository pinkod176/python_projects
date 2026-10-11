"use client";

import { useId } from "react";
import type { Facets } from "@/lib/catalog/query";
import { formatMoney } from "@/lib/format";

type Props = {
  price: NonNullable<Facets["price"]>;
  /** Границы в рублях (строки, как в адресе страницы); пустая строка — «без ограничения». */
  min: string;
  max: string;
  onChange: (next: { min?: string; max?: string }) => void;
};

const THUMB = 28; // px, как в .range (ширина ручки)
const at = (pct: number) => `calc(${pct}% + ${((0.5 - pct / 100) * THUMB).toFixed(2)}px)`;

/**
 * Цена: ползунок с двумя ручками + поля «от» и «до».
 * Ручки шагают по реальным ценам каталога (а не по равномерной шкале), поэтому на каждом шаге что-то меняется,
 * даже если в каталоге две-три очень дорогие работы. Поля принимают любое число. Всё доступно с клавиатуры (← → Home End).
 */
export function PriceRange({ price, min, max, onChange }: Props) {
  const id = useId();
  const pts = price.points;
  const n = pts.length;
  const cur = price.currency;

  const idxFrom = (v: string) => {
    if (!v) return 0;
    const a = Math.round(Number(v) * 100);
    const i = pts.findIndex((x) => x >= a);
    return i === -1 ? n - 1 : i;
  };
  const idxTo = (v: string) => {
    if (!v) return n - 1;
    const a = Math.round(Number(v) * 100);
    let i = n - 1;
    while (i > 0 && pts[i] > a) i--;
    return i;
  };
  const lo = Math.min(idxFrom(min), n - 1);
  const hi = Math.max(lo, idxTo(max));
  const rub = (amount: number) => String(Math.round(amount / 100));
  const pct = (i: number) => (n > 1 ? (i / (n - 1)) * 100 : 0);
  const label = (i: number) => formatMoney({ amount: pts[i], currency: cur });

  if (n < 2) return null;
  return (
    <div>
      <div className="range">
        <div className="range__track" aria-hidden>
          <div className="range__fill" style={{ left: at(pct(lo)), right: `calc(100% - ${at(pct(hi))})` }} />
        </div>
        <input
          type="range"
          min={0}
          max={n - 1}
          step={1}
          value={lo}
          aria-label="Цена от"
          aria-valuetext={label(lo)}
          style={{ zIndex: lo > n / 2 ? 2 : 1 }}
          onChange={(e) => {
            const i = Math.min(Number(e.target.value), hi);
            onChange({ min: i === 0 ? "" : rub(pts[i]) });
          }}
        />
        <input
          type="range"
          min={0}
          max={n - 1}
          step={1}
          value={hi}
          aria-label="Цена до"
          aria-valuetext={label(hi)}
          onChange={(e) => {
            const i = Math.max(Number(e.target.value), lo);
            onChange({ max: i === n - 1 ? "" : rub(pts[i]) });
          }}
        />
      </div>
      <div className="mt-1 flex items-center gap-2">
        <label className="min-w-0 flex-1" htmlFor={`${id}-min`}>
          <span className="sr-only">Цена от, {cur === "RUB" ? "рублей" : cur}</span>
          <input
            id={`${id}-min`}
            inputMode="numeric"
            autoComplete="off"
            className="field !min-h-12 !py-2 text-center tabular-nums"
            placeholder={rub(pts[0])}
            value={min}
            onChange={(e) => onChange({ min: e.target.value.replace(/\D/g, "") })}
          />
        </label>
        <span aria-hidden className="text-copper">—</span>
        <label className="min-w-0 flex-1" htmlFor={`${id}-max`}>
          <span className="sr-only">Цена до, {cur === "RUB" ? "рублей" : cur}</span>
          <input
            id={`${id}-max`}
            inputMode="numeric"
            autoComplete="off"
            className="field !min-h-12 !py-2 text-center tabular-nums"
            placeholder={rub(pts[n - 1])}
            value={max}
            onChange={(e) => onChange({ max: e.target.value.replace(/\D/g, "") })}
          />
        </label>
      </div>
      <p className="mt-2 text-xs text-ink-soft">В каталоге: {label(0)} — {label(n - 1)}</p>
    </div>
  );
}
