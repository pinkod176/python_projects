"use client";

import { createContext, useCallback, useContext, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { lineKey, type ProductCard } from "@/lib/types";

export type CartLine = { card: ProductCard; qty: number };
type Persisted = { cart: Record<string, CartLine>; favs: Record<string, ProductCard> };

const KEY = "zeboogie:v1";
const EMPTY: Persisted = { cart: {}, favs: {} };
const MAX_QTY = 99;

/* ── Хранилище в localStorage с подпиской (useSyncExternalStore): корзина переживает перезагрузку и синхронна между вкладками ── */
let snapshot: Persisted = EMPTY;
let loaded = false;
const listeners = new Set<() => void>();

function read(): Persisted {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw) as Persisted;
    return { cart: parsed.cart ?? {}, favs: parsed.favs ?? {} };
  } catch {
    return EMPTY;
  }
}

function emit(next: Persisted) {
  snapshot = next;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* хранилище недоступно (приватный режим) — работаем в памяти */
  }
  listeners.forEach((l) => l());
}

function subscribe(cb: () => void) {
  if (!loaded) {
    snapshot = read();
    loaded = true;
  }
  listeners.add(cb);
  const onStorage = (e: StorageEvent) => {
    if (e.key === KEY) {
      snapshot = read();
      cb();
    }
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", onStorage);
  };
}
const getSnapshot = () => snapshot;
const getServerSnapshot = () => EMPTY;

type Ctx = {
  lines: CartLine[];
  count: number;
  total: { amount: number; currency: string } | null;
  favorites: ProductCard[];
  isFav: (id: string) => boolean;
  toggleFav: (card: ProductCard) => void;
  add: (card: ProductCard, qty?: number) => void;
  setQty: (id: string, qty: number) => void;
  remove: (id: string) => void;
  clear: () => void;
  /** Обновить сохранённые снимки актуальными данными (цена/название), убрать исчезнувшие. */
  reconcile: (fresh: ProductCard[], goneIds: string[]) => void;
  drawerOpen: boolean;
  setDrawerOpen: (v: boolean) => void;
};

const CartContext = createContext<Ctx | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const state = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const add = useCallback((card: ProductCard, qty = 1) => {
    const key = lineKey(card);
    const cur = snapshot.cart[key];
    const nextQty = Math.min(MAX_QTY, (cur?.qty ?? 0) + qty);
    emit({ ...snapshot, cart: { ...snapshot.cart, [key]: { card, qty: nextQty } } });
    setDrawerOpen(true);
  }, []);
  const setQty = useCallback((id: string, qty: number) => {
    const line = snapshot.cart[id];
    if (!line) return;
    const cart = { ...snapshot.cart };
    if (qty <= 0) delete cart[id];
    else cart[id] = { ...line, qty: Math.min(MAX_QTY, qty) };
    emit({ ...snapshot, cart });
  }, []);
  const remove = useCallback((id: string) => setQty(id, 0), [setQty]);
  const clear = useCallback(() => emit({ ...snapshot, cart: {} }), []);
  const toggleFav = useCallback((card: ProductCard) => {
    const favs = { ...snapshot.favs };
    if (favs[card.vkId]) delete favs[card.vkId];
    else favs[card.vkId] = card;
    emit({ ...snapshot, favs });
  }, []);
  const reconcile = useCallback((fresh: ProductCard[], goneIds: string[]) => {
    const cart = { ...snapshot.cart };
    const favs = { ...snapshot.favs };
    for (const [key, line] of Object.entries(cart)) {
      const f = fresh.find((x) => x.vkId === line.card.vkId);
      if (f) cart[key] = { ...line, card: { ...f, variant: line.card.variant } };
      if (goneIds.includes(line.card.vkId)) delete cart[key];
    }
    for (const f of fresh) if (favs[f.vkId]) favs[f.vkId] = f;
    for (const id of goneIds) delete favs[id];
    emit({ cart, favs });
  }, []);

  const value = useMemo<Ctx>(() => {
    const lines = Object.values(state.cart);
    const priced = lines.filter((l) => l.card.price);
    return {
      lines,
      count: lines.reduce((s, l) => s + l.qty, 0),
      total: priced.length
        ? {
            amount: priced.reduce((s, l) => s + l.card.price!.amount * l.qty, 0),
            currency: priced[0].card.price!.currency,
          }
        : null,
      favorites: Object.values(state.favs),
      isFav: (id) => id in state.favs,
      toggleFav,
      add,
      setQty,
      remove,
      clear,
      reconcile,
      drawerOpen,
      setDrawerOpen,
    };
  }, [state, toggleFav, add, setQty, remove, clear, reconcile, drawerOpen]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): Ctx {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart используется вне CartProvider");
  return ctx;
}
