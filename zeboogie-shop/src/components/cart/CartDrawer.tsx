"use client";

import Link from "next/link";
import { Minus, Plus, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { formatMoney } from "@/lib/format";
import { lineKey } from "@/lib/types";
import { Price } from "@/components/ui/Price";
import { ProductImage } from "@/components/ui/ProductImage";
import { useCart } from "./CartProvider";

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
      className="m-0 ml-auto h-dvh max-h-dvh w-full max-w-md bg-paper p-0 text-ink backdrop:bg-ink/40 open:flex open:flex-col"
    >
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-line px-5">
        <h2 id="cart-title" className="text-2xl">Корзина</h2>
        <button type="button" onClick={() => setDrawerOpen(false)} aria-label="Закрыть корзину" className="grid size-11 place-items-center hover:text-moss">
          <X aria-hidden className="size-6" strokeWidth={1.5} />
        </button>
      </div>

      {lines.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-5 px-8 text-center">
          <p className="font-serif text-2xl">Пока пусто</p>
          <p className="text-ink-soft">Выберите изделия в каталоге — они появятся здесь.</p>
          <Link href="/catalog" onClick={() => setDrawerOpen(false)} className="btn btn-solid">Перейти в каталог</Link>
        </div>
      ) : (
        <>
          <ul className="flex-1 divide-y divide-line overflow-y-auto px-5">
            {lines.map(({ card, qty }) => (
              <li key={lineKey(card)} className="flex gap-4 py-5">
                <Link href={`/product/${card.slug}`} onClick={() => setDrawerOpen(false)} className="mat block w-24 shrink-0 self-start" tabIndex={-1} aria-hidden>
                  <span className="relative block aspect-[4/5]">
                    <ProductImage src={card.image} alt="" sizes="96px" />
                  </span>
                </Link>
                <div className="flex min-w-0 flex-1 flex-col">
                  <Link href={`/product/${card.slug}`} onClick={() => setDrawerOpen(false)} className="leading-snug underline-offset-4 hover:underline">
                    {card.title}
                  </Link>
                  {card.variant && <span className="text-xs text-ink-soft">{card.variant}</span>}
                  <Price price={card.price} className="mt-1 text-sm" />
                  <div className="mt-auto flex items-center justify-between pt-3">
                    <div className="flex items-center border border-line" role="group" aria-label={`Количество: ${card.title}`}>
                      <button type="button" className="grid size-11 place-items-center hover:bg-paper-2" aria-label="Уменьшить количество" onClick={() => setQty(lineKey(card), qty - 1)}>
                        <Minus aria-hidden className="size-4" />
                      </button>
                      <output aria-live="polite" className="min-w-8 text-center">{qty}</output>
                      <button type="button" className="grid size-11 place-items-center hover:bg-paper-2" aria-label="Увеличить количество" onClick={() => setQty(lineKey(card), qty + 1)}>
                        <Plus aria-hidden className="size-4" />
                      </button>
                    </div>
                    <button type="button" onClick={() => remove(lineKey(card))} className="min-h-11 px-2 text-sm text-ink-soft underline underline-offset-4 hover:text-danger">
                      Удалить
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <div className="shrink-0 border-t border-line px-5 py-5">
            <div className="flex items-baseline justify-between">
              <span className="text-ink-soft">Итого</span>
              <span className="font-serif text-2xl">{total ? formatMoney(total) : "—"}</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink-soft">
              Оплата и доставка согласуются с мастерами в личных сообщениях после отправки заказа.
            </p>
            <Link href="/checkout" onClick={() => setDrawerOpen(false)} className="btn btn-solid mt-4 w-full">
              Оформить заказ
            </Link>
          </div>
        </>
      )}
    </dialog>
  );
}
