"use client";

import { useEffect, useRef, useState } from "react";
import type { ProductCard } from "@/lib/types";
import { useCart } from "./CartProvider";

type ValidateItem = { id: string; state: "ok"; card: ProductCard } | { id: string; state: "gone" };

/**
 * Сверяет корзину с каталогом при открытии страницы (цены, исчезнувшие работы) и возвращает сообщения для покупателя.
 * Логика та же, что была в оформлении заказа: ничего не меняется, только вынесена, чтобы её использовали и корзина, и оформление.
 * `recheck()` — повторная проверка (например, после отказа сервера из-за недоступной позиции).
 */
export function useCartValidation() {
  const { lines, reconcile } = useCart();
  const [notice, setNotice] = useState<string[]>([]);
  const checked = useRef(false);

  useEffect(() => {
    if (checked.current || lines.length === 0) return;
    checked.current = true;
    const ids = [...new Set(lines.map((l) => l.card.vkId))];
    void (async () => {
      try {
        const res = await fetch("/api/cart/validate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids }) });
        if (!res.ok) return;
        const { items } = (await res.json()) as { items: ValidateItem[] };
        const gone = items.filter((i) => i.state === "gone").map((i) => i.id);
        const fresh = items.flatMap((i) => (i.state === "ok" ? [i.card] : []));
        const goneTitles = lines.filter((l) => gone.includes(l.card.vkId)).map((l) => l.card.title);
        const changed = lines.filter((l) => {
          const f = fresh.find((x) => x.vkId === l.card.vkId);
          return f && f.price?.amount !== l.card.price?.amount;
        });
        reconcile(fresh, gone);
        setNotice([
          ...(goneTitles.length ? [`Больше недоступны и убраны из корзины: ${goneTitles.join(", ")}.`] : []),
          ...(changed.length ? [`Обновилась цена: ${changed.map((c) => c.card.title).join(", ")}.`] : []),
        ]);
      } catch {
        /* проверка повторится на сервере при отправке заказа */
      }
    })();
  }, [lines, reconcile]);

  return { notice, recheck: () => void (checked.current = false) };
}
