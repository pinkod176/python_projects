"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Grid2x2, Heart, Search, ShoppingBag } from "lucide-react";
import { useCart } from "@/components/cart/CartProvider";
import { CountBadge } from "./HeaderActions";
import { useUi } from "./UiProvider";

/**
 * Нижняя панель быстрых действий на телефоне — в зоне большого пальца: каталог, поиск, избранное, корзина.
 * На странице товара её заменяет своя панель «В корзину», на оформлении заказа панель не нужна.
 * Только настоящие <a>/<button>, зона нажатия — вся четвертинка панели (≥ 80×60).
 */
export function QuickBar() {
  const pathname = usePathname();
  const { count, favorites, setDrawerOpen } = useCart();
  const { setSearchOpen } = useUi();
  if (pathname.startsWith("/product/") || pathname.startsWith("/checkout")) return null;

  return (
    <nav aria-label="Быстрые действия" className="quickbar">
      <div className="quickbar__list">
        <Link href="/catalog" className="quickbar__item" aria-current={pathname.startsWith("/catalog") ? "page" : undefined}>
          <span className="quickbar__icon"><Grid2x2 aria-hidden className="size-[1.4rem]" strokeWidth={1.5} /></span>
          Каталог
        </Link>
        <button type="button" className="quickbar__item" aria-haspopup="dialog" onClick={() => setSearchOpen(true)}>
          <span className="quickbar__icon"><Search aria-hidden className="size-[1.4rem]" strokeWidth={1.5} /></span>
          Поиск
        </button>
        <Link href="/favorites" className="quickbar__item" aria-current={pathname.startsWith("/favorites") ? "page" : undefined} aria-label={`Избранное${favorites.length ? `, ${favorites.length}` : ""}`}>
          <span className="quickbar__icon">
            <Heart aria-hidden className="size-[1.4rem]" strokeWidth={1.5} />
            <CountBadge n={favorites.length} />
          </span>
          Избранное
        </Link>
        <button type="button" className="quickbar__item" aria-haspopup="dialog" aria-label={`Корзина${count ? `, товаров: ${count}` : ""}`} onClick={() => setDrawerOpen(true)}>
          <span className="quickbar__icon">
            <ShoppingBag aria-hidden className="size-[1.4rem]" strokeWidth={1.5} />
            <CountBadge n={count} />
          </span>
          Корзина
        </button>
      </div>
    </nav>
  );
}
