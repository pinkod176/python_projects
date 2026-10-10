"use client";

import { useRouter } from "next/navigation";
import { Check, Minus, Plus, ShoppingBag } from "lucide-react";
import { useEffect, useRef, useState } from "react";
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
  const [done, setDone] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const unavailable = card.availability === "unavailable";

  useEffect(() => () => window.clearTimeout(timer.current), []);

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

  function addToCart() {
    const c = withVariant();
    if (!c) return;
    add(c, qty);
    // Подтверждение на самой кнопке: «В корзину» → «Добавлено» и обратно.
    setDone(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setDone(false), 2400);
  }

  const step = "grid size-[3.25rem] place-items-center transition-colors hover:bg-paper-2 disabled:opacity-40";

  return (
    <div className="space-y-6">
      {options.map((o) => (
        <fieldset key={o.name}>
          <legend className="eyebrow mb-3">{o.name}</legend>
          <div className="relative flex flex-wrap gap-2">
            {o.values.map((v) => (
              <label key={v}>
                <input
                  type="radio"
                  name={o.name}
                  className="sr-only"
                  checked={chosen[o.name] === v}
                  onChange={() => {
                    setChosen((c) => ({ ...c, [o.name]: v }));
                    setError("");
                  }}
                />
                <span className="chip">{v}</span>
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      {error && <p role="alert" className="field-error text-sm text-danger">{error}</p>}

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center rounded-md border border-field" role="group" aria-label="Количество">
          <button type="button" className={`${step} rounded-l-md`} aria-label="Уменьшить количество" disabled={qty <= 1} onClick={() => setQty((q) => q - 1)}>
            <Minus aria-hidden className="size-4" />
          </button>
          <output aria-live="polite" className="min-w-10 text-center tabular-nums">{qty}</output>
          <button type="button" className={`${step} rounded-r-md`} aria-label="Увеличить количество" disabled={qty >= 99} onClick={() => setQty((q) => q + 1)}>
            <Plus aria-hidden className="size-4" />
          </button>
        </div>
        <button type="button" disabled={unavailable} data-done={done} className="btn btn-solid btn-confirm min-w-[10rem] flex-1" onClick={addToCart}>
          <span className="btn-confirm__idle">
            {unavailable ? (
              "Нет в наличии"
            ) : (
              <>
                <ShoppingBag aria-hidden className="size-4" strokeWidth={1.75} /> В корзину
              </>
            )}
          </span>
          <span className="btn-confirm__done" aria-hidden>
            <Check className="size-4" strokeWidth={2} /> Добавлено
          </span>
        </button>
        <span role="status" className="sr-only">{done ? "Товар добавлен в корзину" : ""}</span>
        <FavoriteButton card={card} className="!size-[3.25rem] border border-field" />
      </div>

      {!unavailable && (
        <button
          type="button"
          className="btn btn-ghost w-full"
          onClick={() => {
            const c = withVariant();
            if (c) {
              add(c, qty);
              router.push("/checkout");
            }
          }}
        >
          Оформить заказ сразу
        </button>
      )}
      <div className="text-sm text-ink-soft">
        <p>Заказ отправляется мастерам сообщением во ВКонтакте.</p>
        <a href={vkUrl} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex min-h-11 items-center underline decoration-copper/70 underline-offset-[5px] transition-colors hover:text-wood hover:decoration-wood">Открыть товар в сообществе</a>
      </div>
    </div>
  );
}
