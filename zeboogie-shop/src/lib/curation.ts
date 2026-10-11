import type { ProductBadge, ProductImage } from "./types";

/**
 * Слой «витрины» поверх данных VK: какое фото считать обложкой, как кадрировать, что показывать в hero.
 * Хранится отдельно от исходных данных и фото (src/content/curation.*.json), поэтому всё откатывается удалением записи:
 * исходные файлы и ответы VK не меняются, меняется только порядок и подсказки для вёрстки.
 * Ключ записи — числовой id товара VK (itemId).
 */
export type Curation = {
  /** Номер (с 1) фото, которое должно стать обложкой. По умолчанию — первое. */
  cover?: number;
  /** Номер (с 1) фото для показа при наведении в каталоге. По умолчанию — следующее после обложки. */
  hover?: number;
  /** CSS object-position обложки, например "50% 40%". */
  focalPoint?: string;
  featured?: boolean;
  featuredOrder?: number;
  /** Обложка этой работы становится обложкой её подборки (плитки на главной, меню «Каталог»). */
  collectionCover?: boolean;
  badges?: ProductBadge[];
  /** Заметка для мастерской: почему фото стоит переснять. На сайте не показывается. */
  reshoot?: string;
  /** Снимки «в интерьере» (номера фото) — для блока на главной. */
  interior?: { photo: number; note?: string }[];
};

export type CurationMap = Record<string, Curation>;

/** Убирает служебные ключи (начинаются с «_»). */
export function cleanCuration(raw: unknown): CurationMap {
  if (!raw || typeof raw !== "object") return {};
  return Object.fromEntries(Object.entries(raw).filter(([k]) => !k.startsWith("_"))) as CurationMap;
}

/** Ставит выбранное фото первым, остальные сохраняют исходный порядок. Индексы — с 1, невалидные игнорируются. */
export function applyCover(images: ProductImage[], cover?: number): ProductImage[] {
  if (!cover || cover < 1 || cover > images.length || cover === 1) return images;
  const picked = images[cover - 1];
  return [picked, ...images.filter((_, i) => i !== cover - 1)];
}

/** Второе фото для hover: выбранное мастерской (по исходной нумерации) или следующее после обложки. */
export function pickHover(original: ProductImage[], ordered: ProductImage[], hover?: number): string | undefined {
  if (hover && hover >= 1 && hover <= original.length) {
    const url = original[hover - 1].url;
    if (url !== ordered[0]?.url) return url;
  }
  return ordered[1]?.url;
}
