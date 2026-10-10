"use client";

import { Plus } from "lucide-react";
import type { ProductCard } from "@/lib/types";
import { useCart } from "@/components/cart/CartProvider";

/** Кнопка «в корзину» на карточке. На устройствах с hover — выезжает при наведении, на сенсорных — всегда видна. */
export function QuickAdd({ card }: { card: ProductCard }) {
  const { add } = useCart();
  return (
    <button
      type="button"
      onClick={() => add(card)}
      aria-label={`Добавить «${card.title}» в корзину`}
      className="absolute bottom-[4.4rem] right-3 grid size-11 place-items-center bg-ink text-paper transition-all duration-300 hover:bg-moss focus-visible:opacity-100 sm:right-4 [@media(hover:hover)]:translate-y-1 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:translate-y-0 [@media(hover:hover)]:group-hover:opacity-100"
    >
      <Plus aria-hidden className="size-5" strokeWidth={1.5} />
    </button>
  );
}
