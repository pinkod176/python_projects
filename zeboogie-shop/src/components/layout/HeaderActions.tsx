"use client";

import Link from "next/link";
import { Heart, Menu, Search, ShoppingBag } from "lucide-react";
import { useCart } from "@/components/cart/CartProvider";
import { useUi } from "./UiProvider";

/** Счётчик: при каждом изменении числа элемент пересоздаётся (key) и «подпрыгивает». */
export function CountBadge({ n }: { n: number }) {
  if (!n) return null;
  return (
    <span key={n} aria-hidden className="badge">
      {n}
    </span>
  );
}

/**
 * Иконки справа в шапке. На телефоне (< 768 px) поиск, избранное и корзина живут в нижней панели, а здесь остаётся
 * только бургер; на планшете и десктопе иконки в шапке. Каждая кнопка — настоящий <button>/<a> с зоной нажатия 44×44.
 */
export function HeaderActions() {
  const { count, favorites, setDrawerOpen } = useCart();
  const { menuOpen, setMenuOpen, setSearchOpen } = useUi();
  return (
    <div className="site-header__actions">
      <button type="button" className="icon-btn max-md:hidden" aria-label="Поиск" aria-haspopup="dialog" onClick={() => setSearchOpen(true)}>
        <Search aria-hidden className="size-[1.3rem]" strokeWidth={1.5} />
      </button>
      <Link href="/favorites" className="icon-btn max-md:hidden" aria-label={`Избранное${favorites.length ? `, ${favorites.length}` : ""}`}>
        <Heart aria-hidden className="size-[1.3rem]" strokeWidth={1.5} />
        <CountBadge n={favorites.length} />
      </Link>
      <button type="button" className="icon-btn max-md:hidden" aria-label={`Корзина${count ? `, товаров: ${count}` : ""}`} aria-haspopup="dialog" onClick={() => setDrawerOpen(true)}>
        <ShoppingBag aria-hidden className="size-[1.3rem]" strokeWidth={1.5} />
        <CountBadge n={count} />
      </button>
      <button type="button" className="icon-btn xl:hidden" aria-label="Открыть меню" aria-haspopup="dialog" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}>
        <Menu aria-hidden className="size-[1.5rem]" strokeWidth={1.5} />
      </button>
    </div>
  );
}
