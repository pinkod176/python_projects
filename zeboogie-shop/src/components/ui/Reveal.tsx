"use client";

import { useEffect, useLayoutEffect, useRef, type CSSProperties, type ElementType, type HTMLAttributes, type ReactNode, type Ref } from "react";

/**
 * Плавное появление блоков при прокрутке (fade + лёгкий подъём), только transform/opacity.
 *
 * Как это работает и почему нет «мигания»:
 *  - сервер всегда отдаёт блок видимым (без JS и для поисковиков всё читается);
 *  - после гидрации блоки НИЖЕ экрана прячутся (data-reveal="hidden") и показываются через
 *    IntersectionObserver, когда доходят до экрана — до этого момента пользователь их не видит;
 *  - блоки первого экрана анимируются чистым CSS с первого кадра (prop `first`);
 *  - блоки, появившиеся позже (фильтрация каталога, переход между страницами), анимируются сразу;
 *  - при prefers-reduced-motion ничего не прячется.
 * `delay` задаёт каскад: в сетке карточек — (индекс % 4) × 70 мс.
 * `soft` — без прозрачности (только подъём): для главных фото первого экрана, чтобы не откладывать LCP.
 * Чтение геометрии всех блоков собрано в одну пачку, а запись — в другую: так страница делает один reflow, а не десятки.
 */
type Tag = "div" | "li" | "section" | "article" | "header" | "footer" | "ul" | "ol" | "p" | "h2" | "dl";

type Props = Omit<HTMLAttributes<HTMLElement>, "children"> & {
  as?: Tag;
  /** Задержка в мс (каскад). */
  delay?: number;
  /** Блок виден на первом экране: анимировать CSS-ом с первого кадра. */
  first?: boolean;
  /** Только подъём, без fade (для LCP-фото). */
  soft?: boolean;
  children?: ReactNode;
};

/** true после первой гидрации: все следующие появления элементов — «поздние» (клиентские). */
let hydrated = false;

export function RevealBoot() {
  useEffect(() => {
    hydrated = true;
  }, []);
  return null;
}

let observer: IntersectionObserver | null = null;
function getObserver(): IntersectionObserver {
  if (!observer) {
    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          (entry.target as HTMLElement).dataset.reveal = "shown";
          observer?.unobserve(entry.target);
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
    );
  }
  return observer;
}

const queue: HTMLElement[] = [];
let scheduled = false;

/** Один проход: сначала читаем геометрию всех блоков, затем меняем атрибуты — без «дёргания» layout между ними. */
function flush() {
  scheduled = false;
  const els = queue.splice(0);
  const vh = window.innerHeight;
  const rects = els.map((el) => el.getBoundingClientRect());
  els.forEach((el, i) => {
    const rect = rects[i];
    if (rect.bottom <= 0) return; // уже выше экрана — оставляем видимым
    if (rect.top < vh * 0.92) {
      if (hydrated) el.dataset.reveal = "enter";
      return;
    }
    el.dataset.reveal = "hidden";
    getObserver().observe(el);
  });
}

export function Reveal({ as = "div", delay = 0, first = false, soft = false, className = "", style, children, ...rest }: Props) {
  const ref = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || first) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    queue.push(el);
    if (!scheduled) {
      scheduled = true;
      queueMicrotask(flush); // выполнится до первой отрисовки: мигания нет
    }
    return () => {
      const i = queue.indexOf(el);
      if (i >= 0) queue.splice(i, 1);
      observer?.unobserve(el);
    };
  }, [first]);

  const Component = as as ElementType<HTMLAttributes<HTMLElement> & { ref?: Ref<HTMLElement> }>;
  return (
    <Component
      ref={ref}
      className={`reveal${first ? " reveal-load" : ""}${soft ? " reveal-soft" : ""} ${className}`.trim()}
      style={{ ...style, "--reveal-delay": `${delay}ms` } as CSSProperties}
      {...rest}
    >
      {children}
    </Component>
  );
}
