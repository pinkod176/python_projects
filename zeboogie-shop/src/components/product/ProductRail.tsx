"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ProductCard as Card } from "@/lib/types";
import { ProductCard } from "./ProductCard";

/**
 * Горизонтальная лента карточек («Похожие работы», «Вы смотрели»): на телефоне листается пальцем (scroll-snap),
 * на десктопе — стрелками. Стрелки — настоящие кнопки, на краях ленты гаснут (disabled).
 */
export function ProductRail({ items, label }: { items: Card[]; label: string }) {
  const track = useRef<HTMLUListElement>(null);
  const [edge, setEdge] = useState({ start: true, end: false });

  const measure = useCallback(() => {
    const el = track.current;
    if (!el) return;
    setEdge({ start: el.scrollLeft <= 4, end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 4 });
  }, []);

  useEffect(() => {
    const el = track.current;
    if (!el) return;
    let frame = 0;
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };
    measure();
    el.addEventListener("scroll", onScroll, { passive: true });
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => {
      cancelAnimationFrame(frame);
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
    };
  }, [measure, items.length]);

  const go = (dir: 1 | -1) => track.current?.scrollBy({ left: dir * track.current.clientWidth * 0.85, behavior: "smooth" });

  return (
    <div className="rail" role="region" aria-roledescription="карусель" aria-label={label}>
      <ul ref={track} className="rail__track">
        {items.map((c) => (
          <li key={c.vkId}>
            <ProductCard card={c} headingLevel={3} sizes="(min-width:1200px) 22vw, (min-width:640px) 30vw, 66vw" />
          </li>
        ))}
      </ul>
      <button type="button" className="rail__btn" data-dir="prev" aria-label="Назад" disabled={edge.start} onClick={() => go(-1)}>
        <ChevronLeft aria-hidden className="size-5" strokeWidth={1.5} />
      </button>
      <button type="button" className="rail__btn" data-dir="next" aria-label="Вперёд" disabled={edge.end} onClick={() => go(1)}>
        <ChevronRight aria-hidden className="size-5" strokeWidth={1.5} />
      </button>
    </div>
  );
}
