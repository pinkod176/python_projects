"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { Check, ShoppingBag, SlidersHorizontal, X } from "lucide-react";
import { useCart } from "@/components/cart/CartProvider";
import { Price } from "@/components/ui/Price";
import { ProductImage } from "@/components/ui/ProductImage";
import { useModalDialog } from "@/components/ui/useModalDialog";
import type { ProductCard } from "@/lib/types";
import { FavoriteButton } from "./FavoriteButton";

type Ctx = { open: (card: ProductCard) => void; close: () => void };
const QuickViewContext = createContext<Ctx | null>(null);

export function useQuickView(): Ctx {
  const ctx = useContext(QuickViewContext);
  if (!ctx) throw new Error("useQuickView используется вне QuickViewProvider");
  return ctx;
}

/** Одно окно «Быстрый просмотр» на весь сайт: карточки только сообщают, какую работу показать. Закрывается при смене страницы. */
export function QuickViewProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [state, setState] = useState<{ card: ProductCard; path: string } | null>(null);
  const card = state && state.path === pathname ? state.card : null;
  const value = useMemo<Ctx>(() => ({ open: (c) => setState({ card: c, path: pathname }), close: () => setState(null) }), [pathname]);
  return (
    <QuickViewContext.Provider value={value}>
      {children}
      <QuickViewDialog card={card} onClose={value.close} />
    </QuickViewContext.Provider>
  );
}

function QuickViewDialog({ card, onClose }: { card: ProductCard | null; onClose: () => void }) {
  const dialog = useModalDialog(card !== null, onClose);
  const { add } = useCart();
  const [shown, setShown] = useState<{ id: string; i: number }>({ id: "", i: 0 });
  const photos = card ? [card.image, card.hoverImage].filter((x, i, a): x is string => Boolean(x) && a.indexOf(x) === i) : [];
  const idx = card && shown.id === card.vkId ? shown.i : 0;
  const unavailable = card?.availability === "unavailable";

  return (
    <dialog {...dialog} aria-label={card ? `Быстрый просмотр: ${card.title}` : "Быстрый просмотр"} className="sheet" data-side="center">
      {card && (
        <div className="qv">
          <button type="button" className="icon-btn qv__close" aria-label="Закрыть" onClick={onClose}>
            <X aria-hidden className="size-6" strokeWidth={1.5} />
          </button>
          <div className="qv__media">
            <div className="mat">
              <div className="mat-photo">
                <ProductImage key={photos[idx]} src={photos[idx] ?? null} alt={card.title} focal={idx === 0 ? card.focalPoint : undefined} sizes="(min-width:768px) 28rem, 90vw" quality={82} eager />
              </div>
            </div>
            {photos.length > 1 && (
              <ul className="mt-3 flex gap-2" aria-label="Фото">
                {photos.map((p, i) => (
                  <li key={p}>
                    <button
                      type="button"
                      className="mat block w-14 !p-1"
                      aria-label={`Фото ${i + 1}`}
                      aria-current={i === idx}
                      onClick={() => setShown({ id: card.vkId, i })}
                      style={i === idx ? { outline: "2px solid var(--copper)", outlineOffset: 2 } : { opacity: 0.7 }}
                    >
                      <span className="mat-photo !rounded-[2px]"><ProductImage src={p} alt="" sizes="56px" focal={i === 0 ? card.focalPoint : undefined} /></span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="qv__info">
            {card.categoryTitle && <p className="eyebrow">{card.categoryTitle}</p>}
            <h2 className="mt-2 text-h3 font-light">{card.title}</h2>
            <Price price={card.price} oldPrice={card.oldPrice} size="lg" className="mt-4" />
            {card.availability !== "unknown" && (
              <p className="mt-2 flex items-center gap-2 text-sm">
                <span aria-hidden className={`size-2 rounded-full ${card.availability === "in_stock" ? "bg-moss" : "bg-danger"}`} />
                {card.availability === "in_stock" ? "В наличии" : "Нет в наличии"}
              </p>
            )}
            {card.description && <p className="mt-5 line-clamp-6 whitespace-pre-line text-[0.9375rem] leading-relaxed text-ink-soft">{card.description}</p>}
            <div className="mt-6 flex flex-wrap gap-2">
              {unavailable ? null : card.hasOptions ? (
                <Link href={`/product/${card.slug}`} className="btn btn-solid flex-1" onClick={onClose}>
                  <SlidersHorizontal aria-hidden className="size-4" strokeWidth={1.75} /> Выбрать вариант
                </Link>
              ) : (
                <button
                  type="button"
                  className="btn btn-solid flex-1"
                  onClick={() => {
                    onClose();
                    add(card);
                  }}
                >
                  <ShoppingBag aria-hidden className="size-4" strokeWidth={1.75} /> В корзину
                </button>
              )}
              <FavoriteButton card={card} className="!size-[3.25rem] border border-field" />
            </div>
            <Link href={`/product/${card.slug}`} className="u-link mt-5 inline-flex min-h-11 items-center gap-2 text-sm" onClick={onClose}>
              Подробнее о работе <Check aria-hidden className="hidden" />
            </Link>
          </div>
        </div>
      )}
    </dialog>
  );
}
