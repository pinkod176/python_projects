"use client";

import Link from "next/link";
import { Minus, Plus, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { formatMoney } from "@/lib/format";
import { lineKey } from "@/lib/types";
import { Price } from "@/components/ui/Price";
import { ProductImage } from "@/components/ui/ProductImage";
import { useCart } from "./CartProvider";

const step = "grid size-11 place-items-center transition-colors hover:bg-paper-2";

/** Выезжающая корзина. Анимацию входа/выхода делает CSS (.drawer: translate + opacity, @starting-style). */
export function CartDrawer() {
  const { lines, total, drawerOpen, setDrawerOpen, setQty, remove } = useCart();
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (drawerOpen && !d.open) d.showModal();
    if (!drawerOpen && d.open) d.close();
  }, [drawerOpen]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="cart-title"
      onClose={() => setDrawerOpen(false)}
      onClick={(e) => e.target === ref.current && setDrawerOpen(false)}
      className="drawer"
    >
      <div className="flex h-20 shrink-0 items-center justify-between border-b border-line px-6">
        <h2 id="cart-title" className="text-h3 font-normal">Корзина</h2>
        <button type="button" onClick={() => setDrawerOpen(false)} aria-label="Закрыть корзину" className="icon-btn">
          <X aria-hidden className="size-6" strokeWidth={1.5} />
        </button>
      </div>

      {lines.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-5 px-8 text-center">
          <p className="font-display text-h3 font-light">Пока пусто</p>
          <p className="max-w-xs text-ink-soft">Выберите изделия в каталоге — они появятся здесь.</p>
          <Link href="/catalog" onClick={() => setDrawerOpen(false)} className="btn btn-solid mt-2">Перейти в каталог</Link>
        </div>
      ) : (
        <>
          <ul className="flex-1 divide-y divide-line overflow-y-auto px-6">
            {lines.map(({ card, qty }) => (
              <li key={lineKey(card)} className="flex gap-4 py-6">
                <Link href={`/product/${card.slug}`} onClick={() => setDrawerOpen(false)} className="mat block w-24 shrink-0 self-start !p-1.5" tabIndex={-1} aria-hidden>
                  <span className="mat-photo">
                    <ProductImage src={card.image} alt="" sizes="96px" />
                  </span>
                </Link>
                <div className="flex min-w-0 flex-1 flex-col">
                  <Link href={`/product/${card.slug}`} onClick={() => setDrawerOpen(false)} className="u-link self-start leading-snug">
                    {card.title}
                  </Link>
                  {card.variant && <span className="mt-1 text-xs text-ink-soft">{card.variant}</span>}
                  <Price price={card.price} className="mt-2 text-sm" />
                  <div className="mt-auto flex items-center justify-between gap-2 pt-4">
                    <div className="flex items-center rounded-md border border-field" role="group" aria-label={`Количество: ${card.title}`}>
                      <button type="button" className={`${step} rounded-l-md`} aria-label="Уменьшить количество" onClick={() => setQty(lineKey(card), qty - 1)}>
                        <Minus aria-hidden className="size-4" />
                      </button>
                      <output aria-live="polite" className="min-w-8 text-center tabular-nums">{qty}</output>
                      <button type="button" className={`${step} rounded-r-md`} aria-label="Увеличить количество" onClick={() => setQty(lineKey(card), qty + 1)}>
                        <Plus aria-hidden className="size-4" />
                      </button>
                    </div>
                    <button type="button" onClick={() => remove(lineKey(card))} className="min-h-11 px-1 text-sm text-ink-soft underline-offset-4 transition-colors hover:text-danger hover:underline">
                      Удалить
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <div className="shrink-0 border-t border-line bg-paper-2 px-6 py-6">
            <div className="flex items-baseline justify-between">
              <span className="text-ink-soft">Итого</span>
              <span className="font-display text-h3 font-medium tabular-nums">{total ? formatMoney(total) : "—"}</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink-soft">
              Оплата и доставка согласуются с мастерами в личных сообщениях после отправки заказа.
            </p>
            <Link href="/checkout" onClick={() => setDrawerOpen(false)} className="btn btn-solid mt-5 w-full">
              Оформить заказ
            </Link>
          </div>
        </>
      )}
    </dialog>
  );
}
