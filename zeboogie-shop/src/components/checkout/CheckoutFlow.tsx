"use client";

import Link from "next/link";
import { Check, Copy, ExternalLink, Minus, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useCart } from "@/components/cart/CartProvider";
import { Price } from "@/components/ui/Price";
import { ProductImage } from "@/components/ui/ProductImage";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatMoney } from "@/lib/format";
import { orderRequestSchema } from "@/lib/orders";
import { lineKey, type ProductCard } from "@/lib/types";

type OrderOk = { delivered: boolean; text: string; messageUrl: string; demo: boolean };
type FieldErrors = Partial<Record<"name" | "phone" | "city" | "comment", string>>;

export function CheckoutFlow() {
  const { lines, total, setQty, remove, clear, reconcile } = useCart();
  const [notice, setNotice] = useState<string[]>([]);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<OrderOk | null>(null);
  const [copied, setCopied] = useState(false);
  const checked = useRef(false);

  // Проверка актуальности корзины по данным каталога (цены, исчезнувшие товары).
  useEffect(() => {
    if (checked.current || lines.length === 0) return;
    checked.current = true;
    const ids = [...new Set(lines.map((l) => l.card.vkId))];
    void (async () => {
      try {
        const res = await fetch("/api/cart/validate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids }) });
        if (!res.ok) return;
        const { items } = (await res.json()) as { items: ({ id: string; state: "ok"; card: ProductCard } | { id: string; state: "gone" })[] };
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

  const unavailable = lines.filter((l) => l.card.availability === "unavailable");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormError("");
    const f = new FormData(e.currentTarget);
    const customer = { name: String(f.get("name") ?? ""), phone: String(f.get("phone") ?? ""), city: String(f.get("city") ?? ""), comment: String(f.get("comment") ?? "") };
    const parsed = orderRequestSchema.safeParse({ customer, items: lines.map((l) => ({ vkId: l.card.vkId, variant: l.card.variant, qty: l.qty })) });
    if (!parsed.success) {
      const fe: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        if (issue.path[0] === "customer" && typeof issue.path[1] === "string") fe[issue.path[1] as keyof FieldErrors] ??= issue.message;
        else setFormError(issue.message);
      }
      setErrors(fe);
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      const res = await fetch("/api/order", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(parsed.data) });
      const json = await res.json();
      if (res.status === 409) {
        const problems = json.problems as { vkId: string; reason: "gone" | "unavailable" }[];
        reconcile([], problems.filter((p) => p.reason === "gone").map((p) => p.vkId));
        checked.current = false; // повторно сверим корзину с каталогом
        setFormError("Некоторые товары больше недоступны. Проверьте корзину и отправьте заказ ещё раз.");
      } else if (res.status === 422) {
        setFormError(json.error ?? "Проверьте данные заказа");
      } else if (!res.ok) {
        setFormError(json.error ?? "Не удалось подготовить заказ. Попробуйте ещё раз.");
      } else {
        setResult(json as OrderOk);
        if ((json as OrderOk).delivered) clear();
      }
    } catch {
      setFormError("Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.");
    } finally {
      setBusy(false);
    }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setFormError("Не удалось скопировать автоматически — выделите текст и скопируйте вручную.");
    }
  }

  /* ───── Результат ───── */
  if (result) {
    return (
      <div className="reveal-load mx-auto max-w-2xl">
        {result.delivered ? (
          <>
            <p className="eyebrow">Заказ передан</p>
            <h2 className="mt-3 text-h2 font-light">Заказ отправлен мастерам</h2>
            <p className="mt-5 text-ink-soft">Сообщение с заказом доставлено в сообщество. Мастера свяжутся с вами по указанным контактам.</p>
            <Link href="/catalog" className="btn btn-solid mt-10">Вернуться в каталог</Link>
          </>
        ) : (
          <>
            <p className="eyebrow">Остался один шаг</p>
            <h2 className="mt-3 text-h2 font-light">Заказ подготовлен, но ещё не отправлен</h2>
            <p className="mt-5 text-ink-soft">
              {result.demo
                ? "Это демонстрационный режим: заказ никуда не передаётся. В рабочем режиме здесь будет ссылка на сообщения сообщества."
                : "Скопируйте текст и отправьте его сообщением в сообщество — мастера увидят заказ только после этого."}
            </p>
            <label htmlFor="order-text" className="eyebrow mt-10 block">Текст заказа</label>
            <textarea id="order-text" readOnly value={result.text} rows={Math.min(14, result.text.split("\n").length + 1)} className="field mt-3 font-mono text-sm" onFocus={(e) => e.currentTarget.select()} />
            <div className="mt-5 flex flex-wrap gap-3">
              <button type="button" className="btn btn-solid" onClick={() => void copy(result.text)}>
                {copied ? <Check aria-hidden className="size-4" /> : <Copy aria-hidden className="size-4" />} {copied ? "Скопировано" : "Скопировать текст"}
              </button>
              {!result.demo && (
                <a href={result.messageUrl} target="_blank" rel="noopener noreferrer" className="btn btn-ghost">
                  Открыть сообщения сообщества <ExternalLink aria-hidden className="size-4" />
                </a>
              )}
            </div>
            {formError && <p role="alert" className="field-error mt-4 text-sm text-danger">{formError}</p>}
            {!result.demo && (
              <div className="rule mt-12 pt-8">
                <p className="text-sm text-ink-soft">Отправили сообщение? Тогда можно очистить корзину.</p>
                <button type="button" className="btn btn-ghost mt-4" onClick={() => { clear(); setResult(null); }}>Я отправил заказ, очистить корзину</button>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  if (lines.length === 0) {
    return (
      <EmptyState title="Корзина пуста" action={<Link href="/catalog" className="btn btn-solid">Перейти в каталог</Link>}>
        Добавьте работы, которые вам понравились, и вернитесь сюда.
      </EmptyState>
    );
  }

  /* ───── Корзина + форма ───── */
  const fieldProps = (name: keyof FieldErrors) => ({
    id: name,
    name,
    "aria-invalid": errors[name] ? (true as const) : undefined,
    "aria-describedby": errors[name] ? `${name}-err` : undefined,
    className: "field",
  });
  const err = (name: keyof FieldErrors) =>
    errors[name] && <p id={`${name}-err`} role="alert" className="field-error mt-2 text-sm text-danger">{errors[name]}</p>;
  const label = "mb-2 block text-sm";
  const step = "grid size-11 place-items-center transition-colors hover:bg-paper-2";

  return (
    <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
      <section aria-labelledby="cart-h" className="min-w-0 lg:col-span-7">
        <h2 id="cart-h" className="text-h3 font-normal">Ваш выбор</h2>
        {notice.map((n) => <p key={n} role="status" className="field-error mt-4 rounded-md border border-line border-l-copper bg-paper-2 px-4 py-3 text-sm [border-left-width:3px]">{n}</p>)}
        <ul className="mt-6 divide-y divide-line border-y border-line">
          {lines.map(({ card, qty }) => (
            <li key={lineKey(card)} className="flex gap-5 py-6">
              <Link href={`/product/${card.slug}`} className="mat block w-24 shrink-0 self-start !p-1.5 sm:w-28" aria-label={card.title}>
                <span className="mat-photo"><ProductImage src={card.image} alt="" sizes="112px" /></span>
              </Link>
              <div className="flex min-w-0 flex-1 flex-col">
                <Link href={`/product/${card.slug}`} className="u-link self-start text-lg leading-snug">{card.title}</Link>
                {card.variant && <span className="mt-1 text-xs text-ink-soft">{card.variant}</span>}
                {card.availability === "unavailable" && <span className="field-error mt-1 text-sm text-danger">Нет в наличии — уберите из заказа</span>}
                <Price price={card.price} className="mt-2 text-sm" />
                <div className="mt-auto flex flex-wrap items-center justify-between gap-3 pt-4">
                  <div className="flex items-center rounded-md border border-field" role="group" aria-label={`Количество: ${card.title}`}>
                    <button type="button" className={`${step} rounded-l-md`} aria-label="Уменьшить количество" onClick={() => setQty(lineKey(card), qty - 1)}><Minus aria-hidden className="size-4" /></button>
                    <output className="min-w-8 text-center tabular-nums">{qty}</output>
                    <button type="button" className={`${step} rounded-r-md`} aria-label="Увеличить количество" onClick={() => setQty(lineKey(card), qty + 1)}><Plus aria-hidden className="size-4" /></button>
                  </div>
                  <span className="font-display text-xl font-medium tabular-nums">{card.price ? formatMoney({ amount: card.price.amount * qty, currency: card.price.currency }) : ""}</span>
                  <button type="button" onClick={() => remove(lineKey(card))} className="min-h-11 px-1 text-sm text-ink-soft underline-offset-4 transition-colors hover:text-danger hover:underline">Удалить</button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="form-h" className="min-w-0 lg:col-span-5">
        <div className="rounded-lg border border-line bg-paper-2 p-6 sm:p-8 lg:sticky lg:top-[calc(var(--header-h)+var(--space-3))]">
          <h2 id="form-h" className="text-h3 font-normal">Контакты</h2>
          <p className="mt-2 text-sm text-ink-soft">Мы подготовим текст заказа. Оплата и доставка согласуются с мастерами в личных сообщениях.</p>
          <form onSubmit={onSubmit} noValidate className="mt-8 space-y-5">
            <div>
              <label htmlFor="name" className={label}>Имя <span className="text-copper">*</span></label>
              <input {...fieldProps("name")} autoComplete="name" />{err("name")}
            </div>
            <div>
              <label htmlFor="phone" className={label}>Телефон <span className="text-copper">*</span></label>
              <input {...fieldProps("phone")} type="tel" autoComplete="tel" placeholder="+7 900 000-00-00" />{err("phone")}
            </div>
            <div>
              <label htmlFor="city" className={label}>Город или страна доставки</label>
              <input {...fieldProps("city")} autoComplete="address-level2" />{err("city")}
            </div>
            <div>
              <label htmlFor="comment" className={label}>Комментарий</label>
              <textarea {...fieldProps("comment")} rows={3} />{err("comment")}
            </div>
            {formError && <p role="alert" className="field-error rounded-md border border-danger/40 bg-paper px-4 py-3 text-sm text-danger">{formError}</p>}
            <div className="rule flex items-baseline justify-between pt-6">
              <span className="text-ink-soft">Итого</span>
              <span className="font-display text-h3 font-medium tabular-nums">{total ? formatMoney(total) : "—"}</span>
            </div>
            <button type="submit" disabled={busy || unavailable.length > 0} className="btn btn-solid w-full">
              {busy ? "Проверяем наличие…" : "Подготовить заказ"}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
