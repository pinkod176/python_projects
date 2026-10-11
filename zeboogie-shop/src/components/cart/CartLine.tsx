"use client";

import Link from "next/link";
import { Minus, Plus, X } from "lucide-react";
import { formatMoney } from "@/lib/format";
import { lineKey, type ProductCard } from "@/lib/types";
import { Price } from "@/components/ui/Price";
import { ProductImage } from "@/components/ui/ProductImage";
import { useCart } from "./CartProvider";

type Props = { card: ProductCard; qty: number; size?: "mini" | "page"; onNavigate?: () => void };

/** Строка корзины: фото-обложка, название, вариант, цена, количество (−/+, зона нажатия 44×44) и «Удалить». Используется в мини-корзине и на странице корзины. */
export function CartLine({ card, qty, size = "page", onNavigate }: Props) {
  const { setQty, remove } = useCart();
  const key = lineKey(card);
  const mini = size === "mini";
  const href = `/product/${card.slug}`;
  return (
    <li className="cart-line">
      <Link href={href} onClick={onNavigate} className={`mat cart-line__photo ${mini ? "w-20" : "w-24 sm:w-32"}`} tabIndex={-1} aria-hidden>
        <span className="mat-photo !rounded-[2px]">
          <ProductImage src={card.image} alt="" focal={card.focalPoint} sizes={mini ? "80px" : "128px"} />
        </span>
      </Link>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-start justify-between gap-2">
          <Link href={href} onClick={onNavigate} className="u-link self-start leading-snug">
            {card.title}
          </Link>
          <button type="button" className="icon-btn -mr-2 -mt-2 shrink-0 text-ink-soft" aria-label={`Удалить «${card.title}» из корзины`} onClick={() => remove(key)}>
            <X aria-hidden className="size-[1.15rem]" strokeWidth={1.5} />
          </button>
        </div>
        {card.variant && <span className="mt-0.5 text-xs text-ink-soft">{card.variant}</span>}
        {card.availability === "unavailable" && <span className="field-error mt-1 text-sm text-danger">Нет в наличии — уберите из заказа</span>}
        <div className="mt-auto flex flex-wrap items-center justify-between gap-x-3 gap-y-2 pt-3">
          <div className="qty" role="group" aria-label={`Количество: ${card.title}`}>
            <button type="button" aria-label="Уменьшить количество" onClick={() => setQty(key, qty - 1)}>
              <Minus aria-hidden className="size-4" />
            </button>
            <output aria-live="polite">{qty}</output>
            <button type="button" aria-label="Увеличить количество" onClick={() => setQty(key, qty + 1)}>
              <Plus aria-hidden className="size-4" />
            </button>
          </div>
          {mini || !card.price ? (
            <Price price={card.price} className="text-sm" />
          ) : (
            <span className="font-display text-xl font-medium tabular-nums">{formatMoney({ amount: card.price.amount * qty, currency: card.price.currency })}</span>
          )}
        </div>
      </div>
    </li>
  );
}
