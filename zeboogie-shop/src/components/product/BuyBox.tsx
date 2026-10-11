"use client";

import { useRouter } from "next/navigation";
import { Check, Minus, Plus, ShoppingBag } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import type { ProductCard, ProductOption } from "@/lib/types";
import { useCart } from "@/components/cart/CartProvider";
import { FavoriteButton } from "./FavoriteButton";

type Props = { card: ProductCard; options: ProductOption[]; vkUrl: string };

const noopSubscribe = () => () => {};

/**
 * Покупка: выбор варианта (если есть), количество, «В корзину», избранное.
 * Десктоп — ряд кнопок в колонке справа. Телефон и планшет — закреплённая нижняя панель «♡ + В корзину» в зоне большого пальца;
 * она выносится в body (portal), чтобы ни transform анимаций появления, ни родительские контейнеры не ломали position: fixed.
 */
export function BuyBox({ card, options, vkUrl }: Props) {
  const router = useRouter();
  const { add } = useCart();
  const [qty, setQty] = useState(1);
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const mounted = useSyncExternalStore(noopSubscribe, () => true, () => false);
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

  const addButton = (extra: string) => (
    <button type="button" disabled={unavailable} data-done={done} className={`btn btn-solid btn-confirm ${extra}`} onClick={addToCart}>
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
  );

  return (
    <div className="space-y-5">
      {options.map((o) => (
        <fieldset key={o.name} className="min-w-0 border-0 p-0">
          <legend className="eyebrow mb-3">{o.name}</legend>
          <div className="flex flex-wrap gap-2">
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

      <div className="buy__row">
        <div className="qty" role="group" aria-label="Количество">
          <button type="button" aria-label="Уменьшить количество" disabled={qty <= 1} onClick={() => setQty((q) => q - 1)}>
            <Minus aria-hidden className="size-4" />
          </button>
          <output aria-live="polite">{qty}</output>
          <button type="button" aria-label="Увеличить количество" disabled={qty >= 99} onClick={() => setQty((q) => q + 1)}>
            <Plus aria-hidden className="size-4" />
          </button>
        </div>
        <span className="buy__desktop-add">{addButton("w-full")}</span>
        <span className="buy__desktop-fav"><FavoriteButton card={card} className="!size-[3.25rem] border border-field" /></span>
      </div>
      <span role="status" className="sr-only">{done ? "Товар добавлен в корзину" : ""}</span>

      {!unavailable && (
        <button
          type="button"
          className="btn btn-ghost btn-sm w-full"
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

      {mounted &&
        createPortal(
          <div className="buybar" role="region" aria-label="Покупка">
            {error && <p role="alert" className="field-error buybar__error">{error}</p>}
            <div className="buybar__row">
              <FavoriteButton card={card} className="!size-[3.25rem] border border-field" />
              {addButton("flex-1")}
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}
