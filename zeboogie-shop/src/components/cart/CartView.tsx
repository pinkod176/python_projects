"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { formatMoney, plural } from "@/lib/format";
import { lineKey } from "@/lib/types";
import { EmptyState } from "@/components/ui/EmptyState";
import { CartLine } from "./CartLine";
import { useCart } from "./CartProvider";
import { useCartValidation } from "./useCartValidation";

/** Страница корзины: все строки с количеством, итог сбоку (на телефоне — под списком) и переход к оформлению. */
export function CartView() {
  const { lines, count, total } = useCart();
  const { notice } = useCartValidation();

  if (lines.length === 0) {
    return (
      <EmptyState title="Корзина пуста" action={<Link href="/catalog" className="btn btn-solid">Перейти в каталог</Link>}>
        Добавьте работы, которые вам понравились, и вернитесь сюда.
      </EmptyState>
    );
  }
  const unavailable = lines.some((l) => l.card.availability === "unavailable");
  return (
    <div className="cart-layout">
      <section aria-labelledby="cart-lines-h" className="min-w-0">
        <h2 id="cart-lines-h" className="sr-only">Работы в корзине</h2>
        {notice.map((n) => (
          <p key={n} role="status" className="field-error mb-4 rounded-md border border-line bg-paper-2 px-4 py-3 text-sm [border-left-width:3px] border-l-copper">{n}</p>
        ))}
        <ul className="divide-y divide-line border-y border-line">
          {lines.map(({ card, qty }) => (
            <CartLine key={lineKey(card)} card={card} qty={qty} />
          ))}
        </ul>
        <Link href="/catalog" className="u-link mt-6 inline-flex min-h-11 items-center text-sm">Продолжить покупки</Link>
      </section>
      <aside aria-labelledby="summary-h" className="summary">
        <h2 id="summary-h" className="text-h3 font-normal">Ваш заказ</h2>
        <dl className="mt-5 space-y-2 text-[0.9375rem]">
          <div className="flex justify-between gap-4">
            <dt className="text-ink-soft">{count} {plural(count, ["работа", "работы", "работ"])}</dt>
            <dd className="tabular-nums">{total ? formatMoney(total) : "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-ink-soft">Доставка</dt>
            <dd className="text-right text-ink-soft">согласуется с мастерами</dd>
          </div>
        </dl>
        <div className="mt-5 flex items-baseline justify-between border-t border-line pt-5">
          <span className="text-ink-soft">Итого</span>
          <span className="font-display text-h3 font-medium tabular-nums">{total ? formatMoney(total) : "—"}</span>
        </div>
        {unavailable ? (
          <button type="button" disabled className="btn btn-solid mt-5 w-full">Оформить заказ</button>
        ) : (
          <Link href="/checkout" className="btn btn-solid mt-5 w-full">
            Оформить заказ <ArrowRight aria-hidden className="size-4" />
          </Link>
        )}
        {unavailable && <p role="alert" className="mt-3 text-sm text-danger">Уберите из корзины работы, которых нет в наличии.</p>}
        <p className="mt-4 text-xs leading-relaxed text-ink-soft">Оплата на сайте не принимается: детали вы согласуете с мастерами в личных сообщениях.</p>
      </aside>
    </div>
  );
}
