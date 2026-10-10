"use client";

import { Plus } from "lucide-react";
import type { ProductCard } from "@/lib/types";
import { useCart } from "@/components/cart/CartProvider";

/** Кнопка «в корзину» на карточке. На устройствах с hover появляется при наведении, на сенсорных — всегда видна. */
export function QuickAdd({ card }: { card: ProductCard }) {
  const { add } = useCart();
  return (
    <button
      type="button"
      onClick={() => add(card)}
      aria-label={`Добавить «${card.title}» в корзину`}
      className="card__add grid size-11 place-items-center rounded-md bg-moss text-on-accent hover:bg-wood"
    >
      <Plus aria-hidden className="size-5" strokeWidth={1.5} />
    </button>
  );
}
