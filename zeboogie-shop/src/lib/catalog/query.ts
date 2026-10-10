import { normalizeText } from "@/lib/format";
import type { Product, ProductCard } from "@/lib/types";

export const SORTS = ["new", "price-asc", "price-desc", "name"] as const;
export type Sort = (typeof SORTS)[number];

export type CatalogQuery = {
  q?: string;
  category?: string;
  sort: Sort;
  /** В минимальных единицах валюты. */
  min?: number;
  max?: number;
  inStock?: boolean;
  /** Пары «Название:Значение». */
  attrs: string[];
  page: number;
  pageSize: number;
};

export type Facets = {
  categories: { id: string; title: string; count: number }[];
  price: { min: number; max: number; currency: string } | null;
  attributes: { name: string; values: { value: string; count: number }[] }[];
  hasAvailabilityData: boolean;
};

export type CatalogResult = {
  items: ProductCard[];
  total: number;
  page: number;
  pageSize: number;
  facets: Facets;
};

export function toCard(p: Product): ProductCard {
  return {
    vkId: p.vkId,
    slug: p.slug,
    title: p.title,
    price: p.price,
    oldPrice: p.oldPrice,
    availability: p.availability,
    image: p.images[0]?.url ?? null,
    imageWidth: p.images[0]?.width,
    imageHeight: p.images[0]?.height,
    categoryTitle: p.categories[0]?.title,
    description: p.description,
  };
}

function matchesSearch(p: Product, tokens: string[]): boolean {
  if (!tokens.length) return true;
  const hay = normalizeText(`${p.title} ${p.description} ${p.categories.map((c) => c.title).join(" ")}`);
  return tokens.every((t) => hay.includes(t));
}

const bySort: Record<Sort, (a: Product, b: Product) => number> = {
  new: (a, b) => b.publishedAt - a.publishedAt,
  "price-asc": (a, b) => (a.price?.amount ?? Infinity) - (b.price?.amount ?? Infinity),
  "price-desc": (a, b) => (b.price?.amount ?? -Infinity) - (a.price?.amount ?? -Infinity),
  name: (a, b) => a.title.localeCompare(b.title, "ru"),
};

export function queryProducts(all: Product[], query: CatalogQuery): CatalogResult {
  const active = all.filter((p) => p.status === "active");
  const tokens = normalizeText(query.q ?? "").split(" ").filter(Boolean);

  // Фасеты считаются по товарам, подходящим под поиск (но без остальных фильтров).
  const searched = active.filter((p) => matchesSearch(p, tokens));

  const filtered = searched.filter((p) => {
    if (query.category && !p.categories.some((c) => c.id === query.category)) return false;
    if (query.inStock && p.availability !== "in_stock") return false;
    if (query.min !== undefined && (p.price?.amount ?? -1) < query.min) return false;
    if (query.max !== undefined && (p.price?.amount ?? Infinity) > query.max) return false;
    return query.attrs.every((pair) => {
      const i = pair.indexOf(":");
      const name = pair.slice(0, i);
      const value = pair.slice(i + 1);
      return p.attributes.some((a) => a.name === name && a.value === value);
    });
  });

  filtered.sort(bySort[query.sort]);
  const start = (query.page - 1) * query.pageSize;

  const catMap = new Map<string, { id: string; title: string; count: number }>();
  const attrMap = new Map<string, Map<string, number>>();
  for (const p of searched) {
    for (const c of p.categories) {
      const e = catMap.get(c.id) ?? { id: c.id, title: c.title, count: 0 };
      e.count++;
      catMap.set(c.id, e);
    }
    for (const a of p.attributes) {
      const m = attrMap.get(a.name) ?? new Map<string, number>();
      m.set(a.value, (m.get(a.value) ?? 0) + 1);
      attrMap.set(a.name, m);
    }
  }
  const prices = searched.flatMap((p) => (p.price ? [p.price] : []));

  return {
    items: filtered.slice(start, start + query.pageSize).map(toCard),
    total: filtered.length,
    page: query.page,
    pageSize: query.pageSize,
    facets: {
      categories: [...catMap.values()].sort((a, b) => a.title.localeCompare(b.title, "ru")),
      price: prices.length
        ? {
            min: Math.min(...prices.map((p) => p.amount)),
            max: Math.max(...prices.map((p) => p.amount)),
            currency: prices[0].currency,
          }
        : null,
      // Фильтр по характеристике полезен, только если у неё есть из чего выбирать.
      attributes: [...attrMap]
        .map(([name, values]) => ({
          name,
          values: [...values].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count),
        }))
        .filter((a) => a.values.length > 1 && a.values.length <= 12),
      hasAvailabilityData: searched.some((p) => p.availability !== "unknown"),
    },
  };
}

/** Похожие: сначала из тех же подборок, затем самые новые. */
export function relatedProducts(all: Product[], product: Product, limit = 4): Product[] {
  const cats = new Set(product.categories.map((c) => c.id));
  const others = all.filter((p) => p.status === "active" && p.vkId !== product.vkId);
  const same = others.filter((p) => p.categories.some((c) => cats.has(c.id)));
  const rest = others.filter((p) => !same.includes(p));
  return [...same.sort(bySort.new), ...rest.sort(bySort.new)].slice(0, limit);
}
