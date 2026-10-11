"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { ChevronDown } from "lucide-react";
import { Suspense, useEffect, useId, useRef, useState } from "react";
import { plural } from "@/lib/format";
import { ProductImage } from "@/components/ui/ProductImage";
import { activeTabKey, type NavCategory, type NavTab } from "./nav";

type Props = { tabs: NavTab[]; categories: NavCategory[] };

/**
 * Вкладки шапки на десктопе. «Каталог» раскрывается панелью с подборками и крупными фото:
 *  — мышь: открывается при наведении (с небольшой задержкой, чтобы не мигать), закрывается при уходе курсора;
 *  — клавиатура и касание: кнопка со стрелкой (aria-expanded), Esc закрывает и возвращает фокус на кнопку;
 *  — закрытая панель: visibility: hidden + pointer-events: none + inert, поэтому её невидимое содержимое ничего не перехватывает.
 */
function NavInner({ tabs, categories }: Props) {
  const pathname = usePathname();
  const category = useSearchParams().get("category");
  const active = activeTabKey(tabs, pathname, category);
  const panelId = useId();
  const [open, setOpen] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const root = useRef<HTMLLIElement>(null);
  const caret = useRef<HTMLButtonElement>(null);

  const later = (value: boolean, ms: number) => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setOpen(value), ms);
  };
  useEffect(() => () => window.clearTimeout(timer.current), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOpen(false);
      caret.current?.focus();
    };
    const onDown = (e: PointerEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open]);

  const total = categories.reduce((s, c) => s + c.count, 0);
  const tiles = [...categories].sort((a, b) => b.count - a.count).slice(0, 3);

  return (
    <nav aria-label="Основная навигация" className="nav">
      <ul className="nav__list">
        {tabs.map((t) => {
          const current = active === t.key ? "page" : undefined;
          if (!t.dropdown) {
            return (
              <li key={t.key} className="nav__item">
                <Link href={t.href} aria-current={current} className="nav__tab">{t.label}</Link>
              </li>
            );
          }
          return (
            <li
              key={t.key}
              ref={root}
              className="nav__item"
              onPointerEnter={(e) => e.pointerType === "mouse" && later(true, 90)}
              onPointerLeave={(e) => e.pointerType === "mouse" && later(false, 200)}
              onBlur={(e) => {
                if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false);
              }}
            >
              <Link href={t.href} aria-current={current} className="nav__tab" onClick={() => setOpen(false)}>{t.label}</Link>
              <button
                ref={caret}
                type="button"
                className="nav__caret"
                aria-expanded={open}
                aria-controls={panelId}
                aria-label={open ? "Скрыть разделы каталога" : "Показать разделы каталога"}
                onClick={() => {
                  window.clearTimeout(timer.current);
                  setOpen((v) => !v);
                }}
              >
                <ChevronDown aria-hidden className="size-4" strokeWidth={1.5} />
              </button>

              <div id={panelId} className="catmenu" data-open={open} inert={!open}>
                <div className="catmenu__card">
                  <div>
                    <p className="eyebrow">Каталог</p>
                    <ul className="catmenu__list mt-3">
                      <li>
                        <Link href="/catalog" onClick={() => setOpen(false)}>
                          Все работы <small>{total}</small>
                        </Link>
                      </li>
                      {categories.map((c) => (
                        <li key={c.id}>
                          <Link href={`/catalog?category=${c.id}`} onClick={() => setOpen(false)}>
                            {c.title} <small>{c.count} {plural(c.count, ["работа", "работы", "работ"])}</small>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                  {tiles.length > 0 && (
                    <ul className="catmenu__tiles">
                      {tiles.map((c) => (
                        <li key={c.id}>
                          <Link href={`/catalog?category=${c.id}`} className="catmenu__tile card" onClick={() => setOpen(false)}>
                            <span className="card__media mat block">
                              <span className="mat-photo">
                                <ProductImage src={c.image} alt="" focal={c.imageFocal} sizes="(min-width:1280px) 15vw, 200px" className="card__img" />
                              </span>
                            </span>
                            <span className="mt-3 block font-display text-xl leading-tight">{c.title}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function MainNav(props: Props) {
  return (
    <Suspense fallback={<nav aria-label="Основная навигация" className="nav" />}>
      <NavInner {...props} />
    </Suspense>
  );
}
