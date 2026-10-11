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
  /** «Крупные карточки»: на одну колонку меньше. */
  view?: "grid" | "large";
  /** На телефоне показывать не больше N карточек (остальные скрыты CSS): короткие витрины на главной. */
  trimOnPhone?: number;
  /** Открыта боковая панель фильтров: на ноутбуке 1200–1279 px колонок три, а не четыре. */
  sidebar?: boolean;
};

/** Сетка 2 → 3 → 4 колонки (см. .product-grid). Карточки появляются каскадом: задержка (индекс % 4) × 70 мс. */
export function ProductGrid({ items, startIndex = 0, priorityCount = 0, firstRow = false, numbered = true, view = "grid", trimOnPhone, sidebar, headingLevel = 3 }: Props) {
  return (
    <ul className="product-grid" data-view={view} data-trim={trimOnPhone} data-cols-lg={sidebar ? "3" : undefined}>
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

export function ProductGridSkeleton({ count = 4, view = "grid" }: { count?: number; view?: "grid" | "large" }) {
  return (
    <ul className="product-grid" data-view={view} aria-hidden>
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
