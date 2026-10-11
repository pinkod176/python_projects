"use client";

import Link from "next/link";
import { ShoppingBag, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { formatMoney, plural } from "@/lib/format";
import { lineKey } from "@/lib/types";
import { useModalDialog } from "@/components/ui/useModalDialog";
import { CartLine } from "./CartLine";
import { useCart } from "./CartProvider";

/**
 * Мини-корзина: выезжает справа при добавлении работы (и по иконке корзины). Закрытая — display: none (нативный <dialog>),
 * поэтому ничего не перекрывает страницу и не ловит касания. Анимация — CSS (.sheet: translate + opacity, @starting-style).
 */
export function CartDrawer() {
  const { lines, count, total, drawerOpen, setDrawerOpen } = useCart();
  const pathname = usePathname();
  const dialog = useModalDialog(drawerOpen, () => setDrawerOpen(false));
  const close = () => setDrawerOpen(false);

  return (
    <dialog {...dialog} aria-labelledby="cart-title" className="sheet drawer" data-side="right">
      <div className="flex h-20 shrink-0 items-center justify-between border-b border-line px-5">
        <h2 id="cart-title" className="text-h3 font-normal">
          Корзина{count > 0 && <span className="ml-2 font-sans text-sm text-ink-soft">{count} {plural(count, ["работа", "работы", "работ"])}</span>}
        </h2>
        <button type="button" onClick={close} aria-label="Закрыть корзину" className="icon-btn">
          <X aria-hidden className="size-6" strokeWidth={1.5} />
        </button>
      </div>

      {lines.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-5 px-8 text-center">
          <ShoppingBag aria-hidden className="size-10 text-copper" strokeWidth={1.1} />
          <p className="font-display text-h3 font-light">Пока пусто</p>
          <p className="max-w-xs text-ink-soft">Выберите изделия в каталоге — они появятся здесь.</p>
          <Link href="/catalog" onClick={close} className="btn btn-solid mt-2">Перейти в каталог</Link>
        </div>
      ) : (
        <>
          <ul className="min-h-0 flex-1 divide-y divide-line overflow-y-auto overscroll-contain px-5">
            {lines.map(({ card, qty }) => (
              <CartLine key={lineKey(card)} card={card} qty={qty} size="mini" onNavigate={close} />
            ))}
          </ul>
          <div className="shrink-0 border-t border-line bg-paper-2 px-5 pt-5 pb-[calc(1.25rem+var(--safe-b))]">
            <div className="flex items-baseline justify-between">
              <span className="text-ink-soft">Итого</span>
              <span className="font-display text-h3 font-medium tabular-nums">{total ? formatMoney(total) : "—"}</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink-soft">
              Оплата и доставка согласуются с мастерами в личных сообщениях после отправки заказа.
            </p>
            <div className="mt-4 grid gap-2">
              <Link href="/checkout" onClick={close} className="btn btn-solid w-full">
                Оформить заказ
              </Link>
              {pathname !== "/cart" && (
                <Link href="/cart" onClick={close} className="btn btn-ghost w-full">
                  Перейти в корзину
                </Link>
              )}
            </div>
          </div>
        </>
      )}
    </dialog>
  );
}
