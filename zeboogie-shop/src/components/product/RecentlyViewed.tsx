"use client";

import { useEffect, useSyncExternalStore } from "react";
import type { ProductCard } from "@/lib/types";
import { ProductRail } from "./ProductRail";

const KEY = "zeboogie:viewed";
const MAX = 12;
const EMPTY: ProductCard[] = [];

let snapshot: ProductCard[] = EMPTY;
let loaded = false;
const listeners = new Set<() => void>();

function read(): ProductCard[] {
  try {
    const v = JSON.parse(window.localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(v) ? (v as ProductCard[]) : EMPTY;
  } catch {
    return EMPTY;
  }
}
function subscribe(cb: () => void) {
  if (!loaded) {
    snapshot = read();
    loaded = true;
  }
  listeners.add(cb);
  return () => void listeners.delete(cb);
}

/** Запоминает просмотренную работу (последние 12, на этом устройстве) и показывает остальные просмотренные карточкой-лентой. */
export function RecentlyViewed({ current }: { current: ProductCard }) {
  const list = useSyncExternalStore(subscribe, () => snapshot, () => EMPTY);

  useEffect(() => {
    if (!loaded) {
      snapshot = read();
      loaded = true;
    }
    const next = [current, ...snapshot.filter((c) => c.vkId !== current.vkId)].slice(0, MAX);
    snapshot = next;
    try {
      window.localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* без хранилища список живёт до перезагрузки */
    }
    listeners.forEach((l) => l());
  }, [current]);

  const others = list.filter((c) => c.vkId !== current.vkId);
  if (!others.length) return null;
  return (
    <section className="container-x mt-20 md:mt-28" aria-labelledby="viewed-h">
      <p className="eyebrow">Только что смотрели</p>
      <h2 id="viewed-h" className="mb-8 mt-3 text-h2 font-light">Вы смотрели</h2>
      <ProductRail items={others} label="Вы смотрели" />
    </section>
  );
}
