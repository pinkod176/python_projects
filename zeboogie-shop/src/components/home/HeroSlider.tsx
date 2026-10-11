"use client";

import Link from "next/link";
import { ArrowRight, ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type KeyboardEvent } from "react";
import { Price } from "@/components/ui/Price";
import { ProductImage } from "@/components/ui/ProductImage";
import type { ProductCard } from "@/lib/types";

const AUTOPLAY_MS = 6500;

/**
 * Витрина лучших работ: на десктопе три фото сразу (центральное крупнее), на телефоне — одно большое с «подглядыванием» соседних.
 * Основа — CSS scroll-snap: палец и колесо работают сами, без тяжёлых библиотек. Лента зациклена: три одинаковые копии слайдов,
 * после остановки прокрутки мы бесшумно возвращаемся в среднюю копию, поэтому по краям нет «пустоты», а листать можно бесконечно.
 * Скрипт знает номер текущего слайда, листает стрелками и точками и запускает медленный автоплей (6,5 с).
 * Автоплей стоит на паузе: при наведении мыши, при фокусе внутри, после касания пальцем, при скрытой вкладке, когда блок вне экрана,
 * при prefers-reduced-motion — и по кнопке «Пауза». Точки — настоящие вкладки (role="tablist"), листаются стрелками ← →.
 */
export function HeroSlider({ slides }: { slides: ProductCard[] }) {
  const id = useId();
  const root = useRef<HTMLElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const n = slides.length;
  const loop = n > 1;
  const base = loop ? n : 0; // абсолютный номер первого слайда средней копии
  const items = loop ? [...slides, ...slides, ...slides] : slides;
  const [abs, setAbs] = useState(base); // номер слайда в утроенной ленте
  const [userPaused, setUserPaused] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [focused, setFocused] = useState(false);
  const [inView, setInView] = useState(true);
  const [visible, setVisible] = useState(true);
  // До первого замера считаем, что анимации разрешены: так кнопка «Пауза» есть уже в серверной разметке и страница не «прыгает».
  // Автоплей всё равно стартует не раньше чем через 6,5 с, а к тому моменту prefers-reduced-motion уже прочитан.
  const [reduced, setReduced] = useState(false);
  const current = n ? ((abs % n) + n) % n : 0;

  const step = useCallback(() => {
    const el = track.current;
    const first = el?.children[0] as HTMLElement | undefined;
    if (!el || !first) return 0;
    return first.offsetWidth + (parseFloat(getComputedStyle(el).columnGap) || 0);
  }, []);

  const scrollToAbs = useCallback(
    (i: number, behavior: ScrollBehavior) => {
      const el = track.current;
      if (el) el.scrollTo({ left: i * step(), behavior: reduced ? "auto" : behavior });
    },
    [reduced, step],
  );

  // Стартуем в середине ленты, при изменении размеров окна остаёмся на том же слайде.
  const absRef = useRef(abs);
  useLayoutEffect(() => {
    absRef.current = abs;
  }, [abs]);
  useLayoutEffect(() => {
    const el = track.current;
    if (!el || !loop) return;
    const snap = (instant: boolean) => {
      el.style.scrollSnapType = "none";
      el.scrollLeft = absRef.current * step();
      if (instant) requestAnimationFrame(() => (el.style.scrollSnapType = ""));
    };
    snap(true);
    const ro = new ResizeObserver(() => snap(true));
    ro.observe(el);
    return () => ro.disconnect();
  }, [loop, step]);

  // Текущий слайд — по положению прокрутки; когда лента остановилась у края, перескакиваем в среднюю копию.
  useEffect(() => {
    const el = track.current;
    if (!el) return;
    let frame = 0;
    let settle = 0;
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const s = step();
        if (s) setAbs(Math.max(0, Math.min(items.length - 1, Math.round(el.scrollLeft / s))));
      });
      if (!loop) return;
      window.clearTimeout(settle);
      settle = window.setTimeout(() => {
        const s = step();
        if (!s) return;
        const i = Math.round(el.scrollLeft / s);
        if (i < n || i >= 2 * n) {
          const target = (i < n ? i + n : i - n) * s;
          el.style.scrollSnapType = "none";
          el.scrollLeft = target;
          requestAnimationFrame(() => (el.style.scrollSnapType = ""));
        }
      }, 140);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(settle);
      el.removeEventListener("scroll", onScroll);
    };
  }, [items.length, loop, n, step]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduced(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    const onVis = () => setVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", onVis);
    const io = new IntersectionObserver(([e]) => setInView(e.isIntersecting), { threshold: 0.35 });
    if (root.current) io.observe(root.current);
    return () => {
      mq.removeEventListener("change", sync);
      document.removeEventListener("visibilitychange", onVis);
      io.disconnect();
    };
  }, []);

  const move = useCallback((delta: number) => scrollToAbs(absRef.current + delta, "smooth"), [scrollToAbs]);
  /** К работе номер i (0…n−1) по кратчайшему пути по кольцу. */
  const goTo = (i: number) => {
    let d = (i - current + n) % n;
    if (d > n / 2) d -= n;
    move(d);
  };

  const playing = loop && !reduced && !userPaused && !hovering && !focused && inView && visible;
  useEffect(() => {
    if (!playing) return;
    const t = window.setTimeout(() => move(1), AUTOPLAY_MS);
    return () => window.clearTimeout(t);
  }, [playing, abs, move]);

  const onTabKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const k = e.key;
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(k)) return;
    e.preventDefault();
    const next = k === "Home" ? 0 : k === "End" ? n - 1 : (current + (k === "ArrowRight" ? 1 : -1) + n) % n;
    goTo(next);
    tabs.current[next]?.focus();
  };

  if (n === 0) return null;
  return (
    <section
      ref={root}
      className="hero__stage"
      aria-roledescription="карусель"
      aria-label="Лучшие работы мастерской"
      onPointerEnter={(e) => e.pointerType === "mouse" && setHovering(true)}
      onPointerLeave={(e) => e.pointerType === "mouse" && setHovering(false)}
      onFocus={() => setFocused(true)}
      onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setFocused(false)}
      onTouchStart={() => setUserPaused(true)}
    >
      <div ref={track} className="hero__track no-scrollbar" id={`${id}-track`}>
        {items.map((s, i) => {
          const k = i % n;
          const real = !loop || (i >= base && i < base + n); // средняя копия — «настоящая», остальные — двойники для зацикливания
          return (
            <div
              key={`${s.vkId}-${i}`}
              id={real ? `${id}-slide-${k}` : undefined}
              className="hero__slide reveal-load reveal-soft"
              style={{ "--reveal-delay": `${120 + k * 90}ms` } as CSSProperties}
              data-active={i === abs}
              role={real ? "group" : undefined}
              aria-roledescription={real ? "слайд" : undefined}
              aria-label={real ? `${k + 1} из ${n}` : undefined}
              aria-hidden={real ? undefined : true}
            >
              <Link href={`/product/${s.slug}`} className="hero__card" tabIndex={real ? undefined : -1}>
                <span className="mat hero__mat">
                  <span className="mat-photo hero__photo">
                    <ProductImage
                      src={s.image}
                      alt=""
                      focal={s.focalPoint}
                      sizes="(min-width:1024px) 24rem, 82vw"
                      quality={82}
                      priority={i === base}
                      lowPriority={i !== base}
                      className="hero-img"
                    />
                    <span className="hero__shade" aria-hidden />
                    <span className="hero__caption">
                      <span className="hero__no" aria-hidden>№{String(k + 1).padStart(2, "0")}</span>
                      <span className="hero__name">{s.title}</span>
                      <Price price={s.price} className="hero__price" />
                      <span className="hero__cta">
                        Смотреть работу <ArrowRight aria-hidden className="size-4" strokeWidth={1.75} />
                      </span>
                    </span>
                  </span>
                </span>
              </Link>
            </div>
          );
        })}
      </div>

      {loop && (
        <>
          <button type="button" className="hero__arrow" data-dir="prev" aria-label="Предыдущая работа" aria-controls={`${id}-track`} onClick={() => move(-1)}>
            <ChevronLeft aria-hidden className="size-5" strokeWidth={1.5} />
          </button>
          <button type="button" className="hero__arrow" data-dir="next" aria-label="Следующая работа" aria-controls={`${id}-track`} onClick={() => move(1)}>
            <ChevronRight aria-hidden className="size-5" strokeWidth={1.5} />
          </button>
          <div className="hero__controls">
            <div role="tablist" aria-label="Выбор работы" className="hero__dots" onKeyDown={onTabKey}>
              {slides.map((s, i) => (
                <button
                  key={s.vkId}
                  ref={(el) => {
                    tabs.current[i] = el;
                  }}
                  type="button"
                  role="tab"
                  id={`${id}-tab-${i}`}
                  aria-selected={i === current}
                  aria-controls={`${id}-slide-${i}`}
                  aria-label={`Работа ${i + 1}: ${s.title}`}
                  tabIndex={i === current ? 0 : -1}
                  className="hero__dot"
                  onClick={() => goTo(i)}
                />
              ))}
            </div>
            {!reduced && (
              <button type="button" className="hero__pause" aria-label={userPaused ? "Запустить автопрокрутку" : "Остановить автопрокрутку"} aria-pressed={userPaused} onClick={() => setUserPaused((v) => !v)}>
                {userPaused ? <Play aria-hidden className="size-4" strokeWidth={1.75} /> : <Pause aria-hidden className="size-4" strokeWidth={1.75} />}
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
