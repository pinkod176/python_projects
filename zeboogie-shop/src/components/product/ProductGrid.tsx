import type { ProductCard as Card } from "@/lib/types";
import { ProductCard } from "./ProductCard";

export function ProductGrid({ items, startIndex = 0, priorityCount = 0 }: { items: Card[]; startIndex?: number; priorityCount?: number }) {
  return (
    <ul className="grid grid-cols-2 gap-x-3 gap-y-8 sm:grid-cols-3 sm:gap-x-5 sm:gap-y-12 lg:grid-cols-4 lg:gap-x-6">
      {items.map((c, i) => (
        <li key={c.vkId} className="min-w-0">
          <ProductCard card={c} index={startIndex + i} priority={i < priorityCount} />
        </li>
      ))}
    </ul>
  );
}
