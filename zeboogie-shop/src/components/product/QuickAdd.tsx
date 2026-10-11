"use client";

import Link from "next/link";
import { Plus, SlidersHorizontal } from "lucide-react";
import type { ProductCard } from "@/lib/types";
import { useCart } from "@/components/cart/CartProvider";
import { useQuickView } from "./QuickView";

/**
 * Действия на фото карточки. Телефон: компактная кнопка «+» (всегда на месте, 44×44).
 * Мышь: панель «Быстрый просмотр» + «В корзину», проявляется при наведении.
 * Если у товара есть варианты (размер и т. п.), добавить с карточки нельзя — ссылка на страницу товара.
 */
export function CardActions({ card }: { card: ProductCard }) {
  const { add } = useCart();
  const { open } = useQuickView();
  return (
    <div className="card__actions">
      <button type="button" className="card__quick" onClick={() => open(card)} aria-haspopup="dialog" aria-label={`Быстрый просмотр: ${card.title}`}>
        Быстрый просмотр
      </button>
      {card.hasOptions ? (
        <Link href={`/product/${card.slug}`} className="card__add" aria-label={`Выбрать вариант: ${card.title}`}>
          <SlidersHorizontal aria-hidden className="size-[1.1rem]" strokeWidth={1.75} />
          <span className="card__add-label">Выбрать</span>
        </Link>
      ) : (
        <button type="button" className="card__add" onClick={() => add(card)} aria-label={`Добавить «${card.title}» в корзину`}>
          <Plus aria-hidden className="size-5" strokeWidth={1.75} />
          <span className="card__add-label">В корзину</span>
        </button>
      )}
    </div>
  );
}
