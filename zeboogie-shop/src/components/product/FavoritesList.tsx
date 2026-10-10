"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { useCart } from "@/components/cart/CartProvider";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProductGrid } from "./ProductGrid";
import type { ProductCard } from "@/lib/types";

/** Избранное хранится в браузере; при открытии сверяется с каталогом (цены, исчезнувшие товары). */
export function FavoritesList() {
  const { favorites, reconcile } = useCart();
  const done = useRef(false);
  useEffect(() => {
    if (done.current || favorites.length === 0) return;
    done.current = true;
    void (async () => {
      try {
        const res = await fetch("/api/cart/validate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids: favorites.map((f) => f.vkId) }) });
        if (!res.ok) return;
        const { items } = (await res.json()) as { items: ({ id: string; state: "ok"; card: ProductCard } | { id: string; state: "gone" })[] };
        reconcile(items.flatMap((i) => (i.state === "ok" ? [i.card] : [])), items.filter((i) => i.state === "gone").map((i) => i.id));
      } catch { /* остаются сохранённые данные */ }
    })();
  }, [favorites, reconcile]);

  if (!favorites.length) {
    return (
      <EmptyState title="В избранном пока ничего нет" action={<Link href="/catalog" className="btn btn-solid">Перейти в каталог</Link>}>
        Нажмите на сердечко у понравившейся работы — она сохранится здесь на этом устройстве.
      </EmptyState>
    );
  }
  return <ProductGrid items={favorites} />;
}
