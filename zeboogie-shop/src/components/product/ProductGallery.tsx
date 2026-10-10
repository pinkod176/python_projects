"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef, useState } from "react";
import type { ProductImage as Img } from "@/lib/types";
import { ProductImage } from "@/components/ui/ProductImage";

/**
 * Галерея: фото плавно перетекают друг в друга (crossfade по opacity), миниатюры, стрелки, клавиши ← →
 * и свайп на телефоне. Соседние фото подгружаются заранее, остальные — по мере просмотра.
 */
export function ProductGallery({ images, title }: { images: Img[]; title: string }) {
  const [i, setI] = useState(0);
  const [seen, setSeen] = useState<number[]>([0, 1]);
  const touchX = useRef<number | null>(null);
  const count = images.length;

  function go(n: number) {
    const next = (n + count) % count;
    setI(next);
    setSeen((s) => [...new Set([...s, next, (next + 1) % count])]);
  }

  return (
    <div
      role="group"
      aria-roledescription="галерея"
      aria-label={`Фотографии: ${title}`}
      onKeyDown={(e) => {
        if (count < 2) return;
        if (e.key === "ArrowLeft") go(i - 1);
        if (e.key === "ArrowRight") go(i + 1);
      }}
    >
      <div className="mat relative">
        <div
          className="mat-photo"
          onTouchStart={(e) => (touchX.current = e.touches[0].clientX)}
          onTouchEnd={(e) => {
            if (touchX.current === null || count < 2) return;
            const dx = e.changedTouches[0].clientX - touchX.current;
            touchX.current = null;
            if (Math.abs(dx) > 40) go(dx < 0 ? i + 1 : i - 1);
          }}
        >
          {count === 0 ? (
            <ProductImage src={null} alt={title} sizes="100vw" />
          ) : (
            images.map((img, n) =>
              seen.includes(n) || n === 0 ? (
                <div
                  key={img.url}
                  data-active={n === i}
                  aria-hidden={n !== i}
                  className="absolute inset-0 opacity-0 transition-opacity duration-[800ms] ease-soft data-[active=true]:opacity-100"
                >
                  <ProductImage src={img.url} alt={`${title} — фото ${n + 1} из ${count}`} sizes="(min-width:1024px) 50vw, 100vw" priority={n === 0} />
                </div>
              ) : null,
            )
          )}
        </div>
        {count > 1 && (
          <>
            <button
              type="button"
              onClick={() => go(i - 1)}
              aria-label="Предыдущее фото"
              className="absolute left-5 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-md bg-paper/90 shadow-soft transition-colors hover:bg-paper"
            >
              <ChevronLeft aria-hidden className="size-5" strokeWidth={1.5} />
            </button>
            <button
              type="button"
              onClick={() => go(i + 1)}
              aria-label="Следующее фото"
              className="absolute right-5 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-md bg-paper/90 shadow-soft transition-colors hover:bg-paper"
            >
              <ChevronRight aria-hidden className="size-5" strokeWidth={1.5} />
            </button>
            <span aria-live="polite" className="absolute bottom-5 right-5 rounded-sm bg-footer/80 px-2.5 py-1 text-xs tabular-nums text-on-accent">
              {i + 1} / {count}
            </span>
          </>
        )}
      </div>
      {count > 1 && (
        <ul className="no-scrollbar relative mt-4 flex gap-3 overflow-x-auto p-1">
          {images.map((img, n) => (
            <li key={img.url} className="shrink-0">
              <button
                type="button"
                onClick={() => go(n)}
                aria-label={`Показать фото ${n + 1}`}
                aria-current={n === i}
                className={`mat block w-[4.5rem] !p-1 transition-all duration-300 ease-soft sm:w-20 ${
                  n === i ? "outline outline-2 outline-offset-2 outline-copper" : "opacity-70 hover:opacity-100"
                }`}
              >
                <span className="mat-photo !rounded-[2px]">
                  <ProductImage src={img.url} alt="" sizes="80px" />
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
