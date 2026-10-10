"use client";

import Link from "next/link";
import { createPortal } from "react-dom";
import { Heart, Menu, Search, ShoppingBag, X } from "lucide-react";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useCart } from "@/components/cart/CartProvider";
import { SearchBar } from "./SearchBar";

type NavItem = { href: string; label: string };

/** Счётчик: при каждом изменении числа элемент пересоздаётся (key) и «подпрыгивает». */
function Badge({ n }: { n: number }) {
  if (!n) return null;
  return (
    <span key={n} aria-hidden className="badge">
      {n}
    </span>
  );
}

export function HeaderActions({ nav }: { nav: NavItem[] }) {
  const { count, favorites, setDrawerOpen } = useCart();
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMenuOpen(false);
        setSearchOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <div className="flex items-center">
        <button type="button" className="icon-btn" aria-label="Поиск" aria-expanded={searchOpen} onClick={() => setSearchOpen((v) => !v)}>
          <Search aria-hidden className="size-[1.3rem]" strokeWidth={1.5} />
        </button>
        <Link href="/favorites" className="icon-btn" aria-label={`Избранное${favorites.length ? `, ${favorites.length}` : ""}`}>
          <Heart aria-hidden className="size-[1.3rem]" strokeWidth={1.5} />
          <Badge n={favorites.length} />
        </Link>
        <button type="button" className="icon-btn" aria-label={`Корзина${count ? `, товаров: ${count}` : ""}`} onClick={() => setDrawerOpen(true)}>
          <ShoppingBag aria-hidden className="size-[1.3rem]" strokeWidth={1.5} />
          <Badge n={count} />
        </button>
        <button type="button" className="icon-btn xl:hidden" aria-label="Открыть меню" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}>
          <Menu aria-hidden className="size-[1.4rem]" strokeWidth={1.5} />
        </button>
      </div>

      {searchOpen && (
        <div className="site-header__panel">
          <SearchBar autoFocus onNavigate={() => setSearchOpen(false)} />
        </div>
      )}

      {/* Меню вынесено в body: у шапки есть transform, а он ломает position: fixed у потомков. */}
      {menuOpen &&
        createPortal(
          <div role="dialog" aria-modal="true" aria-label="Меню" className="page-fade fixed inset-0 z-50 flex flex-col bg-paper">
            <div className="container-x flex h-16 shrink-0 items-center justify-between">
              <span className="font-display text-2xl">Меню</span>
              <button type="button" className="icon-btn" aria-label="Закрыть меню" onClick={() => setMenuOpen(false)}>
                <X aria-hidden className="size-6" strokeWidth={1.5} />
              </button>
            </div>
            <nav aria-label="Мобильная навигация" className="container-x flex-1 overflow-y-auto pb-10 pt-4">
              <ul className="rule">
                {nav.map((n, i) => (
                  <li key={n.href} className="reveal-load border-b border-line" style={{ "--reveal-delay": `${80 + i * 60}ms` } as React.CSSProperties}>
                    <Link
                      href={n.href}
                      onClick={() => setMenuOpen(false)}
                      aria-current={pathname === n.href ? "page" : undefined}
                      className="flex min-h-16 items-center justify-between font-display text-[1.9rem] tracking-[-0.01em]"
                    >
                      {n.label}
                      <span aria-hidden className="text-sm text-ink-soft">0{i + 1}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          </div>,
          document.body,
        )}
    </>
  );
}
