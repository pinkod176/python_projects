"use client";

import { useRouter } from "next/navigation";
import { Minus, Plus } from "lucide-react";
import { useState } from "react";
import type { ProductCard, ProductOption } from "@/lib/types";
import { useCart } from "@/components/cart/CartProvider";
import { FavoriteButton } from "./FavoriteButton";

type Props = { card: ProductCard; options: ProductOption[]; vkUrl: string };

export function BuyBox({ card, options, vkUrl }: Props) {
  const router = useRouter();
  const { add } = useCart();
  const [qty, setQty] = useState(1);
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const unavailable = card.availability === "unavailable";

  function withVariant(): ProductCard | null {
    const missing = options.find((o) => !chosen[o.name]);
    if (missing) {
      setError(`Выберите: ${missing.name.toLowerCase()}`);
      return null;
    }
    setError("");
    const variant = options.map((o) => `${o.name}: ${chosen[o.name]}`).join(", ");
    return variant ? { ...card, variant } : card;
  }

  return (
    <div className="space-y-6">
      {options.map((o) => (
        <fieldset key={o.name}>
          <legend className="eyebrow mb-3">{o.name}</legend>
          <div className="flex flex-wrap gap-2">
            {o.values.map((v) => (
              <label key={v} className={`flex min-h-11 cursor-pointer items-center border px-4 ${chosen[o.name] === v ? "border-ink bg-ink text-paper" : "border-line hover:border-ink"}`}>
                <input type="radio" name={o.name} className="sr-only" checked={chosen[o.name] === v} onChange={() => { setChosen((c) => ({ ...c, [o.name]: v })); setError(""); }} />
                {v}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center border border-line" role="group" aria-label="Количество">
          <button type="button" className="grid size-12 place-items-center hover:bg-paper-2 disabled:opacity-40" aria-label="Уменьшить количество" disabled={qty <= 1} onClick={() => setQty((q) => q - 1)}>
            <Minus aria-hidden className="size-4" />
          </button>
          <output aria-live="polite" className="min-w-10 text-center">{qty}</output>
          <button type="button" className="grid size-12 place-items-center hover:bg-paper-2 disabled:opacity-40" aria-label="Увеличить количество" disabled={qty >= 99} onClick={() => setQty((q) => q + 1)}>
            <Plus aria-hidden className="size-4" />
          </button>
        </div>
        <button type="button" disabled={unavailable} className="btn btn-solid min-w-0 flex-1" onClick={() => { const c = withVariant(); if (c) add(c, qty); }}>
          {unavailable ? "Нет в наличии" : "В корзину"}
        </button>
        <FavoriteButton card={card} className="border border-line" />
      </div>

      {!unavailable && (
        <button type="button" className="btn btn-ghost w-full" onClick={() => { const c = withVariant(); if (c) { add(c, qty); router.push("/checkout"); } }}>
          Оформить заказ сразу
        </button>
      )}
      <p className="text-sm text-ink-soft">
        Заказ отправляется мастерам сообщением во ВКонтакте.{" "}
        <a href={vkUrl} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4 hover:text-ink">Открыть товар в сообществе</a>
      </p>
    </div>
  );
}
