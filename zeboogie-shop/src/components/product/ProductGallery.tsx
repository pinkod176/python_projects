"use client";

import { ChevronLeft, ChevronRight, Expand, X } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState, type CSSProperties, type KeyboardEvent, type MouseEvent } from "react";
import { ProductImage } from "@/components/ui/ProductImage";
import { useModalDialog } from "@/components/ui/useModalDialog";
import type { ProductImage as Img } from "@/lib/types";

type Props = { images: Img[]; title: string; focal?: string };

/**
 * Галерея товара. Главное фото — горизонтальная лента со scroll-snap: на телефоне листается пальцем (без JS-обработчиков касаний,
 * поэтому не конфликтует с жестами браузера), на десктопе — стрелками, миниатюрами и клавишами ← →.
 * Клик (тап) по фото открывает крупный просмотр с увеличением. Обложка (первое фото) идёт первой, остальные — в исходном порядке.
 * Точки на телефоне — вкладки (role="tablist") с зоной нажатия 44×44.
 */
export function ProductGallery({ images, title, focal }: Props) {
  const id = useId();
  const track = useRef<HTMLUListElement>(null);
  const [i, setI] = useState(0);
  const [zoom, setZoom] = useState<number | null>(null);
  const count = images.length;

  const go = useCallback((n: number, behavior: ScrollBehavior = "smooth") => {
    const el = track.current;
    if (!el) return;
    const next = Math.max(0, Math.min(count - 1, n));
    el.scrollTo({ left: next * el.clientWidth, behavior });
  }, [count]);

  useEffect(() => {
    const el = track.current;
    if (!el) return;
    let frame = 0;
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setI(Math.round(el.scrollLeft / Math.max(1, el.clientWidth))));
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      el.removeEventListener("scroll", onScroll);
    };
  }, []);

  const onKey = (e: KeyboardEvent) => {
    if (count < 2) return;
    const step = e.key === "ArrowLeft" ? -1 : e.key === "ArrowRight" ? 1 : 0;
    if (!step) return;
    e.preventDefault();
    go(i + step);
    // Фокус идёт за фото: иначе Enter открыл бы просмотр предыдущего кадра, который уже ушёл за край ленты.
    if ((e.target as HTMLElement).closest(".gallery__photo")) {
      track.current?.querySelectorAll<HTMLElement>(".gallery__photo")[Math.max(0, Math.min(count - 1, i + step))]?.focus({ preventScroll: true });
    }
  };

  // Пропорции рамки на десктопе — как у обложки (но не уже 0,62 и не шире квадрата).
  const first = images[0];
  const ratio = first?.width && first?.height ? Math.max(0.62, Math.min(1, first.width / first.height)) : 0.8;

  return (
    <div className="gallery" style={{ "--ratio": ratio.toFixed(3) } as CSSProperties} role="group" aria-roledescription="галерея" aria-label={`Фотографии: ${title}`} onKeyDown={onKey}>
      {count > 1 && (
        <ul className="gallery__thumbs no-scrollbar" aria-label="Миниатюры">
          {images.map((img, n) => (
            <li key={img.url}>
              <button type="button" className="gallery__thumb mat" onClick={() => go(n)} aria-label={`Показать фото ${n + 1}`} aria-current={n === i}>
                <span className="mat-photo !rounded-[2px]">
                  <ProductImage src={img.url} alt="" sizes="72px" focal={n === 0 ? focal : undefined} />
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="gallery__main">
        <div className="mat gallery__mat">
          <ul ref={track} className="gallery__track no-scrollbar" id={`${id}-track`}>
            {count === 0 ? (
              <li className="gallery__slide"><div className="mat-photo gallery__photo"><ProductImage src={null} alt={title} sizes="100vw" /></div></li>
            ) : (
              images.map((img, n) => (
                <li key={img.url} className="gallery__slide" aria-label={`Фото ${n + 1} из ${count}`}>
                  <button type="button" className="mat-photo gallery__photo" onClick={() => setZoom(n)} aria-label={`Увеличить фото ${n + 1} из ${count}`} tabIndex={n === i ? 0 : -1}>
                    <ProductImage
                      src={img.url}
                      alt={`${title} — фото ${n + 1} из ${count}`}
                      fit="contain"
                      focal={n === 0 ? focal : undefined}
                      sizes="(min-width:1024px) 40rem, 100vw"
                      quality={82}
                      priority={n === 0}
                      eager={n === 1}
                    />
                    <span className="gallery__zoom" aria-hidden><Expand className="size-[1.1rem]" strokeWidth={1.5} /></span>
                  </button>
                </li>
              ))
            )}
          </ul>
          {count > 1 && (
            <>
              <button type="button" className="gallery__arrow" data-dir="prev" aria-label="Предыдущее фото" aria-controls={`${id}-track`} disabled={i === 0} onClick={() => go(i - 1)}>
                <ChevronLeft aria-hidden className="size-5" strokeWidth={1.5} />
              </button>
              <button type="button" className="gallery__arrow" data-dir="next" aria-label="Следующее фото" aria-controls={`${id}-track`} disabled={i === count - 1} onClick={() => go(i + 1)}>
                <ChevronRight aria-hidden className="size-5" strokeWidth={1.5} />
              </button>
              <div role="tablist" aria-label="Фото" className="gallery__dots">
                {images.map((img, n) => (
                  <button key={img.url} type="button" role="tab" aria-selected={n === i} aria-label={`Фото ${n + 1}`} tabIndex={n === i ? 0 : -1} className="gallery__dot" onClick={() => go(n)} />
                ))}
              </div>
              <span aria-live="polite" className="gallery__count">{i + 1} / {count}</span>
            </>
          )}
        </div>
      </div>

      <Lightbox images={images} title={title} start={zoom} onClose={() => setZoom(null)} onIndex={(n) => go(n, "auto")} />
    </div>
  );
}

/** Крупный просмотр: стрелки, клавиши ← → Esc, клик по фото — увеличение ×1,8 к точке клика. */
function Lightbox({ images, title, start, onClose, onIndex }: { images: Img[]; title: string; start: number | null; onClose: () => void; onIndex: (n: number) => void }) {
  const dialog = useModalDialog(start !== null, onClose);
  return (
    <dialog {...dialog} aria-label={`Фото: ${title}`} className="sheet lightbox" data-side="full">
      {/* Содержимое монтируется только при открытом окне и с нуля при каждом открытии: номер фото и увеличение не «залипают». */}
      {start !== null && <LightboxBody key={start} images={images} title={title} initial={start} onClose={onClose} onIndex={onIndex} />}
    </dialog>
  );
}

function LightboxBody({ images, title, initial, onClose, onIndex }: { images: Img[]; title: string; initial: number; onClose: () => void; onIndex: (n: number) => void }) {
  const [i, setI] = useState(initial);
  const [zoomed, setZoomed] = useState<{ x: number; y: number } | null>(null);
  const set = (n: number) => {
    const next = Math.max(0, Math.min(images.length - 1, n));
    setI(next);
    setZoomed(null);
    onIndex(next);
  };
  const img = images[i];
  const toggle = (e: MouseEvent<HTMLButtonElement>) => {
    if (zoomed) return setZoomed(null);
    const r = e.currentTarget.getBoundingClientRect();
    setZoomed({ x: ((e.clientX - r.left) / r.width) * 100, y: ((e.clientY - r.top) / r.height) * 100 });
  };
  if (!img) return null;
  return (
    <div
      className="contents"
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") set(i - 1);
        if (e.key === "ArrowRight") set(i + 1);
      }}
    >
      <button type="button" className="icon-btn lightbox__close" aria-label="Закрыть просмотр" onClick={onClose}>
        <X aria-hidden className="size-6" strokeWidth={1.5} />
      </button>
      <div className="lightbox__stage">
        <button
          type="button"
          className="lightbox__frame"
          aria-label={zoomed ? "Уменьшить" : "Увеличить"}
          onClick={toggle}
          style={{
            aspectRatio: img.width && img.height ? `${img.width} / ${img.height}` : "4 / 5",
            maxWidth: img.width ? `min(100%, ${Math.round(img.width * 1.7)}px)` : undefined,
            transform: zoomed ? "scale(1.8)" : undefined,
            transformOrigin: zoomed ? `${zoomed.x}% ${zoomed.y}%` : undefined,
            cursor: zoomed ? "zoom-out" : "zoom-in",
          }}
        >
          <ProductImage src={img.url} alt={`${title} — фото ${i + 1} из ${images.length}`} fit="contain" sizes="100vw" quality={82} eager />
        </button>
      </div>
      {images.length > 1 && (
        <>
          <button type="button" className="lightbox__arrow" data-dir="prev" aria-label="Предыдущее фото" disabled={i === 0} onClick={() => set(i - 1)}>
            <ChevronLeft aria-hidden className="size-6" strokeWidth={1.5} />
          </button>
          <button type="button" className="lightbox__arrow" data-dir="next" aria-label="Следующее фото" disabled={i === images.length - 1} onClick={() => set(i + 1)}>
            <ChevronRight aria-hidden className="size-6" strokeWidth={1.5} />
          </button>
          <span aria-live="polite" className="lightbox__count">{i + 1} / {images.length}</span>
        </>
      )}
    </div>
  );
}
