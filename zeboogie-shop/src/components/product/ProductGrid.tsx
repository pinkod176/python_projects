import type { ProductCard as Card } from "@/lib/types";
import { Reveal } from "@/components/ui/Reveal";
import { ProductCard } from "./ProductCard";

type Props = {
  items: Card[];
  startIndex?: number;
  /** Сколько первых фото грузить с приоритетом (LCP). */
  priorityCount?: number;
  /** Первый ряд виден сразу при открытии страницы — анимировать его с первого кадра (иначе — при прокрутке). */
  firstRow?: boolean;
  /** Уровень заголовка названий: 2 — если над сеткой только h1 (каталог), 3 — под секцией h2. */
  headingLevel?: 2 | 3;
  /** Показывать номера «№01». */
  numbered?: boolean;
  /** На телефоне — горизонтальная лента вместо длинной колонки. */
  rail?: boolean;
};

/** Сетка 4 → 3 → 2 → 1 колонка (см. .product-grid). Карточки появляются каскадом: задержка (индекс % 4) × 70 мс. */
export function ProductGrid({ items, startIndex = 0, priorityCount = 0, firstRow = false, numbered = true, rail = false, headingLevel = 3 }: Props) {
  return (
    <ul className={`product-grid${rail ? " product-grid--rail relative" : ""}`}>
      {items.map((c, i) => (
        <Reveal key={c.vkId} as="li" className="min-w-0" delay={(i % 4) * 70} first={firstRow && i < 4} soft={firstRow && i < 4}>
          <ProductCard
            card={c}
            index={numbered ? startIndex + i : undefined}
            priority={i === 0 && priorityCount > 0}
            eager={i > 0 && i < priorityCount}
            headingLevel={headingLevel}
          />
        </Reveal>
      ))}
    </ul>
  );
}

export function ProductGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <ul className="product-grid" aria-hidden>
      {Array.from({ length: count }).map((_, i) => (
        <li key={i}>
          <div className="mat">
            <div className="skeleton aspect-[4/5]" />
          </div>
          <div className="skeleton mt-4 h-4 w-2/3" />
          <div className="skeleton mt-2 h-4 w-1/4" />
        </li>
      ))}
    </ul>
  );
}
