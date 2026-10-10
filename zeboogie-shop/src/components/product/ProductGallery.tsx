"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import type { ProductImage as Img } from "@/lib/types";
import { ProductImage } from "@/components/ui/ProductImage";

/** Галерея: большое фото, миниатюры, стрелки и клавиатура (← →). Без фото показывается заглушка. */
export function ProductGallery({ images, title }: { images: Img[]; title: string }) {
  const [i, setI] = useState(0);
  const count = images.length;
  const go = (n: number) => setI((n + count) % count);

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
        <div className="relative aspect-[4/5] overflow-hidden bg-paper-3">
          <ProductImage src={images[i]?.url} alt={`${title} — фото ${i + 1} из ${Math.max(count, 1)}`} sizes="(min-width:1024px) 45vw, 100vw" priority />
        </div>
        {count > 1 && (
          <>
            <button type="button" onClick={() => go(i - 1)} aria-label="Предыдущее фото" className="absolute left-4 top-1/2 grid size-11 -translate-y-1/2 place-items-center bg-paper/90 hover:bg-paper">
              <ChevronLeft aria-hidden className="size-5" strokeWidth={1.5} />
            </button>
            <button type="button" onClick={() => go(i + 1)} aria-label="Следующее фото" className="absolute right-4 top-1/2 grid size-11 -translate-y-1/2 place-items-center bg-paper/90 hover:bg-paper">
              <ChevronRight aria-hidden className="size-5" strokeWidth={1.5} />
            </button>
          </>
        )}
      </div>
      {count > 1 && (
        <ul className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {images.map((img, n) => (
            <li key={img.url} className="shrink-0">
              <button
                type="button"
                onClick={() => setI(n)}
                aria-label={`Показать фото ${n + 1}`}
                aria-current={n === i}
                className={`mat block w-16 sm:w-20 ${n === i ? "outline outline-2 outline-ink" : "opacity-70 hover:opacity-100"}`}
              >
                <span className="relative block aspect-[4/5]">
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
