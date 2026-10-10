"use client";

import { Heart } from "lucide-react";
import type { ProductCard } from "@/lib/types";
import { useCart } from "@/components/cart/CartProvider";

export function FavoriteButton({ card, className = "" }: { card: ProductCard; className?: string }) {
  const { isFav, toggleFav } = useCart();
  const on = isFav(card.vkId);
  return (
    <button
      type="button"
      onClick={() => toggleFav(card)}
      aria-pressed={on}
      aria-label={on ? `Убрать «${card.title}» из избранного` : `Добавить «${card.title}» в избранное`}
      className={`grid size-11 place-items-center bg-paper/90 text-ink transition-colors hover:bg-paper ${className}`}
    >
      <Heart aria-hidden className={`size-5 transition-transform duration-300 ${on ? "scale-110 fill-wood text-wood" : ""}`} strokeWidth={1.5} />
    </button>
  );
}
