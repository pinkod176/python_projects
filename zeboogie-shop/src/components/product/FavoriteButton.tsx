"use client";

import { Heart } from "lucide-react";
import { useState } from "react";
import type { ProductCard } from "@/lib/types";
import { useCart } from "@/components/cart/CartProvider";

/** Сердечко: плавно заполняется (opacity + transform с лёгкой «пружиной») и пускает кольцо-пульс при добавлении. */
export function FavoriteButton({ card, className = "" }: { card: ProductCard; className?: string }) {
  const { isFav, toggleFav } = useCart();
  const on = isFav(card.vkId);
  const [burst, setBurst] = useState(0);
  return (
    <button
      type="button"
      onClick={() => {
        if (!on) setBurst((b) => b + 1);
        toggleFav(card);
      }}
      aria-pressed={on}
      aria-label={on ? `Убрать «${card.title}» из избранного` : `Добавить «${card.title}» в избранное`}
      className={`fav ${className}`}
    >
      <Heart aria-hidden className="fav__icon" strokeWidth={1.5} />
      <Heart aria-hidden className="fav__icon fav__filled" strokeWidth={1.5} />
      {burst > 0 && on && <span key={burst} aria-hidden className="fav__ring" />}
    </button>
  );
}
