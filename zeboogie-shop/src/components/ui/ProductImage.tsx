"use client";

import Image from "next/image";
import { ImageOff } from "lucide-react";
import { useCallback, type SyntheticEvent } from "react";

type Props = {
  src: string | null | undefined;
  alt: string;
  sizes: string;
  /** Главное фото первого экрана (LCP): грузится сразу, с высоким приоритетом и без fade-in. */
  priority?: boolean;
  /** Фото первого экрана попроще (например, первый ряд каталога): грузится сразу, без fade-in. */
  eager?: boolean;
  className?: string;
};

/**
 * Фото товара. Родитель задаёт пропорции (.mat-photo → aspect-ratio 4/5), поэтому вёрстка не прыгает.
 * Плавная подгрузка: пока файл грузится, фото прозрачно (виден песочный плейсхолдер с мерцанием),
 * по событию load оно проявляется. Уже загруженные/кэшированные фото не мигают — их не прячем.
 * Если фото нет или оно не загрузилось, показывается спокойная заглушка, а не «битая» картинка.
 */
export function ProductImage({ src, alt, sizes, priority, eager, className = "" }: Props) {
  const ref = useCallback(
    (img: HTMLImageElement | null) => {
      if (img && !priority && !eager && !img.complete) img.dataset.loading = "true";
    },
    [priority, eager],
  );
  const settle = (e: SyntheticEvent<HTMLImageElement>) => {
    e.currentTarget.dataset.loading = "false";
  };

  if (!src) {
    return (
      <div role="img" aria-label={alt} className="grid h-full w-full place-items-center bg-paper-3 text-ink-soft">
        <ImageOff aria-hidden className="size-8" strokeWidth={1.25} />
      </div>
    );
  }
  return (
    <Image
      ref={ref}
      src={src}
      alt={alt}
      fill
      sizes={sizes}
      loading={priority || eager ? "eager" : undefined}
      fetchPriority={priority ? "high" : undefined}
      onLoad={settle}
      onError={settle}
      className={`img-fade object-cover ${className}`}
    />
  );
}
