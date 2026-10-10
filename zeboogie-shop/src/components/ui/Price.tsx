import { discountPercent, formatMoney } from "@/lib/format";
import type { Money } from "@/lib/types";

type Props = { price: Money | null; oldPrice?: Money | null; size?: "sm" | "lg"; className?: string };

/** Цена. Старая цена и скидка показываются только если они пришли из источника. */
export function Price({ price, oldPrice, size = "sm", className = "" }: Props) {
  if (!price) {
    return <span className={`text-ink-soft ${className}`}>Цена по запросу</span>;
  }
  const big = size === "lg";
  return (
    <span className={`inline-flex flex-wrap items-baseline gap-x-3 gap-y-0 ${className}`}>
      <span className={big ? "font-serif text-3xl md:text-4xl" : "font-medium"}>{formatMoney(price)}</span>
      {oldPrice && (
        <>
          <s className="text-ink-soft text-sm" aria-label={`Прежняя цена ${formatMoney(oldPrice)}`}>
            {formatMoney(oldPrice)}
          </s>
          <span className="text-sm text-wood">−{discountPercent(price, oldPrice)}%</span>
        </>
      )}
    </span>
  );
}
