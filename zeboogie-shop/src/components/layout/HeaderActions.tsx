"use client";

import Link from "next/link";
import { Heart, Menu, Search, ShoppingBag, X } from "lucide-react";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useCart } from "@/components/cart/CartProvider";
import { SearchBar } from "./SearchBar";

type NavItem = { href: string; label: string };

function Badge({ n }: { n: number }) {
  if (!n) return null;
  return (
    <span aria-hidden className="absolute right-0.5 top-0.5 grid min-w-[1.1rem] place-items-center rounded-full bg-wood px-1 text-[0.65rem] leading-[1.1rem] text-paper">
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

  const btn = "relative grid size-11 place-items-center hover:text-moss";
  return (
    <>
      <div className="flex items-center">
        <button type="button" className={btn} aria-label="Поиск" aria-expanded={searchOpen} onClick={() => setSearchOpen((v) => !v)}>
          <Search aria-hidden className="size-[1.3rem]" strokeWidth={1.5} />
        </button>
        <Link href="/favorites" className={btn} aria-label={`Избранное${favorites.length ? `, ${favorites.length}` : ""}`}>
          <Heart aria-hidden className="size-[1.3rem]" strokeWidth={1.5} />
          <Badge n={favorites.length} />
        </Link>
        <button type="button" className={btn} aria-label={`Корзина${count ? `, товаров: ${count}` : ""}`} onClick={() => setDrawerOpen(true)}>
          <ShoppingBag aria-hidden className="size-[1.3rem]" strokeWidth={1.5} />
          <Badge n={count} />
        </button>
        <button type="button" className={`${btn} lg:hidden`} aria-label="Открыть меню" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}>
          <Menu aria-hidden className="size-[1.4rem]" strokeWidth={1.5} />
        </button>
      </div>

      {searchOpen && (
        <div className="absolute inset-x-0 top-full border-b border-line bg-paper">
          <div className="container-x py-4">
            <SearchBar autoFocus onNavigate={() => setSearchOpen(false)} />
          </div>
        </div>
      )}

      {menuOpen && (
        <div role="dialog" aria-modal="true" aria-label="Меню" className="fixed inset-0 z-50 flex flex-col bg-paper lg:hidden">
          <div className="container-x flex h-16 items-center justify-between">
            <span className="font-serif text-2xl">Меню</span>
            <button type="button" className={btn} aria-label="Закрыть меню" onClick={() => setMenuOpen(false)}>
              <X aria-hidden className="size-6" strokeWidth={1.5} />
            </button>
          </div>
          <nav aria-label="Мобильная навигация" className="container-x flex-1 overflow-y-auto pb-10">
            <ul className="rule">
              {nav.map((n) => (
                <li key={n.href} className="border-b border-line">
                  <Link
                    href={n.href}
                    onClick={() => setMenuOpen(false)}
                    aria-current={pathname === n.href ? "page" : undefined}
                    className="flex min-h-14 items-center font-serif text-2xl"
                  >
                    {n.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      )}
    </>
  );
}
