"use client";

import Link from "next/link";
import { Check, ChevronDown, Copy, ExternalLink } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useCart } from "@/components/cart/CartProvider";
import { useCartValidation } from "@/components/cart/useCartValidation";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProductImage } from "@/components/ui/ProductImage";
import { formatMoney, plural } from "@/lib/format";
import { orderRequestSchema } from "@/lib/orders";
import { lineKey } from "@/lib/types";

type OrderOk = { delivered: boolean; text: string; messageUrl: string; demo: boolean };
type Field = "name" | "phone" | "city" | "comment";
type FieldErrors = Partial<Record<Field, string>>;
type Values = Record<Field, string>;

/** Шаги: контакты → доставка → оплата и подтверждение. Поля каждого шага проверяются той же схемой (zod), что и на сервере. */
const STEPS: { key: string; title: string; fields: Field[] }[] = [
  { key: "contacts", title: "Контакты", fields: ["name", "phone"] },
  { key: "delivery", title: "Доставка", fields: ["city", "comment"] },
  { key: "payment", title: "Оплата", fields: [] },
];

export function CheckoutFlow() {
  const { lines, count, total, clear, reconcile } = useCart();
  const { notice, recheck } = useCartValidation();
  const [step, setStep] = useState(0);
  const [values, setValues] = useState<Values>({ name: "", phone: "", city: "", comment: "" });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<OrderOk | null>(null);
  const [copied, setCopied] = useState(false);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const moved = useRef(false);

  // После перехода между шагами фокус — на первое поле нового шага (при первом показе фокус не забираем, чтобы не открывать клавиатуру).
  useEffect(() => {
    if (!moved.current) return;
    panel.current?.querySelector<HTMLElement>("input, textarea, button[data-first]")?.focus({ preventScroll: true });
  }, [step]);

  const unavailable = lines.filter((l) => l.card.availability === "unavailable");

  /** Ошибки полей текущего шага; остальные поля не мешают переходу. */
  function validate(fields: Field[]): FieldErrors {
    const parsed = orderRequestSchema.safeParse({
      customer: values,
      items: lines.map((l) => ({ vkId: l.card.vkId, variant: l.card.variant, qty: l.qty })),
    });
    if (parsed.success) return {};
    const fe: FieldErrors = {};
    for (const issue of parsed.error.issues) {
      const f = issue.path[1];
      if (issue.path[0] === "customer" && typeof f === "string" && fields.includes(f as Field)) fe[f as Field] ??= issue.message;
    }
    return fe;
  }

  async function submitOrder() {
    setFormError("");
    const parsed = orderRequestSchema.safeParse({
      customer: values,
      items: lines.map((l) => ({ vkId: l.card.vkId, variant: l.card.variant, qty: l.qty })),
    });
    if (!parsed.success) {
      const fe: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        if (issue.path[0] === "customer" && typeof issue.path[1] === "string") fe[issue.path[1] as Field] ??= issue.message;
        else setFormError(issue.message);
      }
      setErrors(fe);
      // Вернём на первый шаг с ошибкой.
      const bad = STEPS.findIndex((s) => s.fields.some((f) => fe[f]));
      if (bad >= 0) goTo(bad);
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
        recheck(); // повторно сверим корзину с каталогом
        setFormError("Некоторые товары больше недоступны. Проверьте корзину и отправьте заказ ещё раз.");
      } else if (res.status === 422) {
        setFormError(json.error ?? "Проверьте данные заказа");
      } else if (!res.ok) {
        setFormError(json.error ?? "Не удалось подготовить заказ. Попробуйте ещё раз.");
      } else {
        setResult(json as OrderOk);
        if ((json as OrderOk).delivered) clear();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    } catch {
      setFormError("Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.");
    } finally {
      setBusy(false);
    }
  }

  function goTo(i: number) {
    moved.current = true;
    setStep(i);
    setFormError("");
    panel.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    if (step < STEPS.length - 1) {
      const fe = validate(STEPS[step].fields);
      setErrors((cur) => ({ ...cur, ...Object.fromEntries(STEPS[step].fields.map((f) => [f, fe[f]])) }));
      if (Object.keys(fe).length) {
        panel.current?.querySelector<HTMLElement>("[aria-invalid='true']")?.focus();
        return;
      }
      goTo(step + 1);
    } else {
      void submitOrder();
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

  /* ───── Шаги + сводка ───── */
  const set = (f: Field) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setValues((v) => ({ ...v, [f]: e.target.value }));
    if (errors[f]) setErrors((cur) => ({ ...cur, [f]: undefined }));
  };
  const fieldProps = (name: Field) => ({
    id: name,
    name,
    value: values[name],
    onChange: set(name),
    "aria-invalid": errors[name] ? (true as const) : undefined,
    "aria-describedby": errors[name] ? `${name}-err` : undefined,
    className: "field",
  });
  const err = (name: Field) =>
    errors[name] && <p id={`${name}-err`} role="alert" className="field-error mt-2 text-sm text-danger">{errors[name]}</p>;
  const label = "mb-2 block text-sm";
  const last = step === STEPS.length - 1;
  const primary = last ? (busy ? "Проверяем наличие…" : "Подготовить заказ") : "Далее";
  const totalText = total ? formatMoney(total) : "—";

  return (
    <div className="cart-layout">
      <section aria-labelledby="step-h" className="min-w-0">
        {notice.map((n) => (
          <p key={n} role="status" className="field-error mb-4 rounded-md border border-line bg-paper-2 px-4 py-3 text-sm [border-left-width:3px] border-l-copper">{n}</p>
        ))}

        <ol className="steps" aria-label="Шаги оформления">
          {STEPS.map((s, i) => {
            const state = i === step ? "active" : i < step ? "done" : "todo";
            return (
              <li key={s.key} className="steps__item" data-state={state} data-done={i < step}>
                {i < step ? (
                  <button type="button" className="steps__btn" onClick={() => goTo(i)} aria-label={`Вернуться к шагу «${s.title}»`}>
                    <span className="steps__num"><Check aria-hidden className="size-4" strokeWidth={2} /></span>
                    <span className="steps__label">{s.title}</span>
                  </button>
                ) : (
                  <span className="steps__btn" aria-current={i === step ? "step" : undefined}>
                    <span className="steps__num">{i + 1}</span>
                    <span className="steps__label">{s.title}</span>
                  </span>
                )}
              </li>
            );
          })}
        </ol>

        <form id="checkout-form" onSubmit={onSubmit} noValidate className="mt-8">
          <div key={step} ref={panel} className="step-panel max-w-xl">
            <h2 id="step-h" className="text-h3 font-normal">{STEPS[step].title}</h2>

            {step === 0 && (
              <div className="mt-6 space-y-5">
                <p className="text-sm text-ink-soft">Как с вами связаться, чтобы подтвердить заказ.</p>
                <div>
                  <label htmlFor="name" className={label}>Имя <span className="text-copper">*</span></label>
                  <input {...fieldProps("name")} autoComplete="name" enterKeyHint="next" />{err("name")}
                </div>
                <div>
                  <label htmlFor="phone" className={label}>Телефон <span className="text-copper">*</span></label>
                  <input {...fieldProps("phone")} type="tel" inputMode="tel" autoComplete="tel" enterKeyHint="next" placeholder="+7 900 000-00-00" />{err("phone")}
                </div>
              </div>
            )}

            {step === 1 && (
              <div className="mt-6 space-y-5">
                <p className="text-sm text-ink-soft">Стоимость и сроки доставки мастера рассчитают после получения заказа и согласуют с вами лично.</p>
                <div>
                  <label htmlFor="city" className={label}>Город или страна доставки</label>
                  <input {...fieldProps("city")} autoComplete="address-level2" enterKeyHint="next" />{err("city")}
                </div>
                <div>
                  <label htmlFor="comment" className={label}>Комментарий</label>
                  <textarea {...fieldProps("comment")} rows={4} placeholder="Адрес, удобное время, пожелания к упаковке" />{err("comment")}
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="mt-6 space-y-6">
                <p className="text-ink-soft">
                  Оплата на сайте не принимается. Мы подготовим текст заказа — отправьте его мастерам сообщением, а способ оплаты вы согласуете с ними лично.
                </p>
                <dl className="divide-y divide-line rounded-lg border border-line bg-paper-2 text-[0.9375rem]">
                  {([
                    ["Имя", values.name, 0],
                    ["Телефон", values.phone, 0],
                    ["Доставка", values.city || "уточним в сообщениях", 1],
                  ] as const).map(([k, v, to]) => (
                    <div key={k} className="flex items-center justify-between gap-4 px-4 py-3">
                      <dt className="text-ink-soft">{k}</dt>
                      <dd className="min-w-0 flex-1 truncate text-right">{v}</dd>
                      <button type="button" className="u-link min-h-11 shrink-0 px-1 text-sm" onClick={() => goTo(to)} aria-label={`Изменить: ${k}`}>Изменить</button>
                    </div>
                  ))}
                </dl>
                {values.comment && <p className="text-sm text-ink-soft">Комментарий: {values.comment}</p>}
                {unavailable.length > 0 && <p role="alert" className="text-sm text-danger">Уберите из корзины работы, которых нет в наличии, — иначе заказ не получится подготовить.</p>}
              </div>
            )}

            {formError && <p role="alert" className="field-error mt-6 rounded-md border border-danger/40 bg-paper px-4 py-3 text-sm text-danger">{formError}</p>}

            <div className="mt-8 flex flex-wrap items-center gap-3 max-lg:hidden">
              <button type="submit" disabled={busy || (last && unavailable.length > 0)} className="btn btn-solid min-w-[12rem]">{primary}</button>
              {step > 0 && <button type="button" className="btn btn-ghost" onClick={() => goTo(step - 1)}>Назад</button>}
            </div>
            {step > 0 && <button type="button" className="u-link mt-6 min-h-11 text-sm lg:hidden" onClick={() => goTo(step - 1)}>← Назад</button>}
          </div>
        </form>
      </section>

      <aside aria-label="Ваш заказ" className="summary">
        <button
          type="button"
          className="flex min-h-11 w-full items-center justify-between gap-3 text-left lg:pointer-events-none"
          aria-expanded={summaryOpen}
          aria-controls="summary-lines"
          onClick={() => setSummaryOpen((v) => !v)}
        >
          <span className="text-h3 font-display">Ваш заказ</span>
          <span className="flex items-center gap-2 text-sm text-ink-soft">
            {count} {plural(count, ["работа", "работы", "работ"])}
            <ChevronDown aria-hidden className={`size-4 transition-transform duration-300 lg:hidden ${summaryOpen ? "rotate-180" : ""}`} />
          </span>
        </button>
        <ul id="summary-lines" className={`mt-4 space-y-4 ${summaryOpen ? "" : "max-lg:hidden"}`}>
          {lines.map(({ card, qty }) => (
            <li key={lineKey(card)} className="flex items-center gap-3">
              <span className="mat w-14 shrink-0 !p-1">
                <span className="mat-photo !rounded-[2px]"><ProductImage src={card.image} alt="" focal={card.focalPoint} sizes="56px" /></span>
              </span>
              <span className="min-w-0 flex-1 text-sm leading-snug">
                <span className="line-clamp-2">{card.title}</span>
                <span className="text-ink-soft">{qty} × {card.price ? formatMoney(card.price) : "—"}</span>
              </span>
            </li>
          ))}
        </ul>
        <div className="mt-5 flex items-baseline justify-between border-t border-line pt-5">
          <span className="text-ink-soft">Итого</span>
          <span className="font-display text-h3 font-medium tabular-nums">{totalText}</span>
        </div>
        <Link href="/cart" className="u-link mt-4 inline-flex min-h-11 items-center text-sm max-lg:hidden">Изменить состав заказа</Link>
      </aside>

      {/* Телефон и планшет: итог и главная кнопка закреплены внизу, в зоне большого пальца */}
      <div className="checkout-bar">
        <div className="min-w-0 flex-1 leading-tight">
          <p className="text-xs text-ink-soft">Итого</p>
          <p className="font-display text-xl font-medium tabular-nums">{totalText}</p>
        </div>
        <button type="submit" form="checkout-form" disabled={busy || (last && unavailable.length > 0)} className="btn btn-solid min-w-[11rem]">{primary}</button>
      </div>
    </div>
  );
}
