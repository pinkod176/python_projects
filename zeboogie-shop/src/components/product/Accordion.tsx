"use client";

import { Plus } from "lucide-react";
import { useId, useState, type ReactNode } from "react";

export type AccItem = { id: string; title: string; content: ReactNode; open?: boolean };

/**
 * Аккордеон: каждая секция — кнопка с aria-expanded и область role="region". Раскрывается плавно (строка сетки 0fr → 1fr + проявление),
 * закрытое содержимое скрыто от клавиатуры и скринридеров (visibility: hidden). Секции независимы: можно открыть несколько.
 */
export function Accordion({ items }: { items: AccItem[] }) {
  const base = useId();
  const [open, setOpen] = useState<Record<string, boolean>>(() => Object.fromEntries(items.map((i) => [i.id, Boolean(i.open)])));
  return (
    <div>
      {items.map((it) => {
        const on = open[it.id];
        return (
          <section key={it.id} className="acc">
            <h2 className="!font-sans !text-base !font-medium !tracking-normal">
              <button
                type="button"
                className="acc__head"
                id={`${base}-${it.id}-h`}
                aria-expanded={on}
                aria-controls={`${base}-${it.id}-p`}
                onClick={() => setOpen((o) => ({ ...o, [it.id]: !o[it.id] }))}
              >
                {it.title}
                <Plus aria-hidden className="acc__icon size-5" strokeWidth={1.5} />
              </button>
            </h2>
            <div id={`${base}-${it.id}-p`} role="region" aria-labelledby={`${base}-${it.id}-h`} className="acc__panel" data-open={on}>
              <div className="acc__inner">
                <div className="pb-5 pt-1 text-[0.9375rem] leading-relaxed text-ink-soft">{it.content}</div>
              </div>
            </div>
          </section>
        );
      })}
    </div>
  );
}
