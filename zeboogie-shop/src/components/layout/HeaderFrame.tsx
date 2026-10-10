"use client";

import { useEffect, useRef, type ReactNode } from "react";

const SCROLLED_AT = 8; // после этой прокрутки появляется полупрозрачное «стекло»
const COMPACT_AT = 96; // выше этой отметки шапку не сжимаем
const MIN_DELTA = 6; // игнорируем дрожание меньше 6 px, чтобы шапка не мигала

/**
 * Оболочка шапки. Следит за прокруткой и выставляет data-атрибуты; всё остальное — CSS на transform/opacity:
 *  - прокрутка вниз → шапка «сжимается» и получает blur (data-compact="true");
 *  - прокрутка вверх → возвращается к исходному размеру.
 * Высота шапки в потоке не меняется, поэтому вёрстка не «прыгает».
 */
export function HeaderFrame({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let lastY = window.scrollY;
    let frame = 0;

    const apply = (initial = false) => {
      frame = 0;
      const y = Math.max(0, window.scrollY);
      const dy = y - lastY;
      el.dataset.scrolled = String(y > SCROLLED_AT);
      if (y < COMPACT_AT) el.dataset.compact = "false";
      else if (initial || dy > MIN_DELTA) el.dataset.compact = "true";
      else if (dy < -MIN_DELTA) el.dataset.compact = "false";
      if (Math.abs(dy) > MIN_DELTA) lastY = y;
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(() => apply());
    };

    apply(true);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <header ref={ref} className="site-header" data-scrolled="false" data-compact="false">
      {children}
    </header>
  );
}
