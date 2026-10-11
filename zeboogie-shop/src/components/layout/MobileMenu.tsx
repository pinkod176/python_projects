"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Heart, ShoppingBag, X } from "lucide-react";
import { Suspense } from "react";
import { useCart } from "@/components/cart/CartProvider";
import { useModalDialog } from "@/components/ui/useModalDialog";
import { brand } from "@/content/brand";
import { plural } from "@/lib/format";
import { CountBadge } from "./HeaderActions";
import { activeTabKey, type NavCategory, type NavTab } from "./nav";
import { useUi } from "./UiProvider";

type Props = { tabs: NavTab[]; categories: NavCategory[] };

function MenuInner({ tabs, categories }: Props) {
  const { menuOpen, setMenuOpen } = useUi();
  const { count, favorites, setDrawerOpen } = useCart();
  const pathname = usePathname();
  const category = useSearchParams().get("category");
  const dialog = useModalDialog(menuOpen, () => setMenuOpen(false));
  const active = activeTabKey(tabs, pathname, category);
  const close = () => setMenuOpen(false);
  const total = categories.reduce((s, c) => s + c.count, 0);

  // В меню подборки показываются списком под «Каталогом», а не отдельными вкладками.
  const topLevel = tabs.filter((t) => !t.categoryId);

  return (
    <dialog {...dialog} aria-label="Меню" className="sheet" data-side="full">
      <div className="container-x flex shrink-0 items-center justify-between" style={{ height: "var(--header-h)" }}>
        <span className="font-display text-[1.75rem] font-medium">{brand.name}</span>
        <button type="button" className="icon-btn" aria-label="Закрыть меню" onClick={close}>
          <X aria-hidden className="size-6" strokeWidth={1.5} />
        </button>
      </div>
      <nav aria-label="Мобильная навигация" className="container-x flex-1 overflow-y-auto overscroll-contain pb-[calc(var(--space-4)+var(--safe-b))] pt-2">
        <ul className="rule">
          {topLevel.map((t, i) => (
            <li key={t.key} className="reveal-load border-b border-line" style={{ "--reveal-delay": `${60 + i * 55}ms` } as React.CSSProperties}>
              <Link href={t.href} onClick={close} aria-current={active === t.key ? "page" : undefined} className="menu__item">
                {t.label}
                {t.dropdown ? <small className="font-sans text-sm text-ink-soft">{total} {plural(total, ["работа", "работы", "работ"])}</small> : <span aria-hidden className="font-sans text-sm text-ink-soft">0{i + 1}</span>}
              </Link>
              {t.dropdown && categories.length > 0 && (
                <ul className="menu__sub -mt-1 mb-3 pl-1">
                  {categories.map((c) => (
                    <li key={c.id}>
                      <Link href={`/catalog?category=${c.id}`} onClick={close} aria-current={active === c.id ? "page" : undefined}>
                        {c.title}
                        <small className="text-xs">{c.count}</small>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
        <div className="mt-8 grid grid-cols-2 gap-2">
          <Link href="/favorites" onClick={close} className="btn btn-ghost relative">
            <Heart aria-hidden className="size-[1.1rem]" strokeWidth={1.5} /> Избранное
            <CountBadge n={favorites.length} />
          </Link>
          <button
            type="button"
            className="btn btn-ghost relative"
            onClick={() => {
              close();
              setDrawerOpen(true);
            }}
          >
            <ShoppingBag aria-hidden className="size-[1.1rem]" strokeWidth={1.5} /> Корзина
            <CountBadge n={count} />
          </button>
        </div>
      </nav>
    </dialog>
  );
}

export function MobileMenu(props: Props) {
  // Меню нужно только на экранах < 1280 px, но элемент остаётся в DOM закрытым (display: none у закрытого dialog).
  return (
    <Suspense fallback={null}>
      <MenuInner {...props} />
    </Suspense>
  );
}
