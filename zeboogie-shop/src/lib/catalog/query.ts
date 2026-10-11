import { FORMAT_ORDER, normalizeText } from "@/lib/format";
import type { Product, ProductBadge, ProductCard } from "@/lib/types";

export const SORTS = ["new", "price-asc", "price-desc", "popular", "name"] as const;
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
  /** points — все различные цены каталога по возрастанию (в копейках): ползунок цены шагает по реальным ценам. */
  price: { min: number; max: number; currency: string; points: number[] } | null;
  attributes: { name: string; values: { value: string; count: number }[] }[];
  hasAvailabilityData: boolean;
  /** Есть ли у товаров число лайков: без него «Популярные» — это не «популярные», а выбор мастерской. */
  hasPopularity: boolean;
};

export type CatalogResult = {
  items: ProductCard[];
  total: number;
  page: number;
  pageSize: number;
  facets: Facets;
};

const NEW_WINDOW_SEC = 30 * 24 * 3600;

/** Метки карточки: «Новинка» вычисляется по дате публикации, остальные задаёт мастерская (слой curation). */
export function cardBadges(p: Product, nowSec = Math.floor(Date.now() / 1000)): ProductBadge[] {
  const out = new Set<ProductBadge>(p.badges ?? []);
  if (p.publishedAt > 0 && nowSec - p.publishedAt >= 0 && nowSec - p.publishedAt < NEW_WINDOW_SEC) out.add("new");
  return [...out];
}

export function toCard(p: Product): ProductCard {
  const cover = p.images[0];
  return {
    vkId: p.vkId,
    slug: p.slug,
    title: p.title,
    price: p.price,
    oldPrice: p.oldPrice,
    availability: p.availability,
    image: cover?.url ?? null,
    imageWidth: cover?.width,
    imageHeight: cover?.height,
    focalPoint: p.focalPoint,
    hoverImage: p.hoverImage ?? p.images[1]?.url,
    categoryId: p.categories[0]?.id,
    categoryTitle: p.categories[0]?.title,
    description: p.description,
    badges: cardBadges(p),
    hasOptions: p.options.length > 0 || undefined,
  };
}

function matchesSearch(p: Product, tokens: string[]): boolean {
  if (!tokens.length) return true;
  const hay = normalizeText(`${p.title} ${p.description} ${p.categories.map((c) => c.title).join(" ")}`);
  return tokens.every((t) => hay.includes(t));
}

/** Характеристики: внутри одной группы (например, «Формат: S» и «Формат: M») значения складываются через «или», между группами — через «и». */
function matchesAttrs(p: Product, pairs: string[]): boolean {
  const groups = new Map<string, string[]>();
  for (const pair of pairs) {
    const i = pair.indexOf(":");
    const name = pair.slice(0, i);
    groups.set(name, [...(groups.get(name) ?? []), pair.slice(i + 1)]);
  }
  return [...groups].every(([name, values]) => p.attributes.some((a) => a.name === name && values.includes(a.value)));
}

const featuredRank = (p: Product) => (p.featured ? (p.featuredOrder ?? 99) : 1000);

const bySort: Record<Sort, (a: Product, b: Product) => number> = {
  new: (a, b) => b.publishedAt - a.publishedAt,
  "price-asc": (a, b) => (a.price?.amount ?? Infinity) - (b.price?.amount ?? Infinity),
  "price-desc": (a, b) => (b.price?.amount ?? -Infinity) - (a.price?.amount ?? -Infinity),
  // Лайки VK, если они есть; затем «выбор мастерской» (hero), затем новизна.
  popular: (a, b) =>
    (b.popularity ?? -1) - (a.popularity ?? -1) || featuredRank(a) - featuredRank(b) || b.publishedAt - a.publishedAt,
  name: (a, b) => a.title.localeCompare(b.title, "ru"),
};

/** Значения характеристики: «Формат» — в порядке размеров мастерской, остальные — по числу товаров. */
function sortValues(name: string, values: { value: string; count: number }[]) {
  if (name === "Формат") {
    const rank = (v: string) => {
      const i = FORMAT_ORDER.indexOf(v);
      return i === -1 ? FORMAT_ORDER.length : i;
    };
    return values.sort((a, b) => rank(a.value) - rank(b.value) || a.value.localeCompare(b.value, "ru"));
  }
  return values.sort((a, b) => b.count - a.count);
}

/** Различные цены по возрастанию; у очень больших каталогов — не больше 120 равномерно взятых значений (края сохраняются). */
function pricePoints(amounts: number[]): number[] {
  const unique = [...new Set(amounts)].sort((a, b) => a - b);
  if (unique.length <= 120) return unique;
  const step = (unique.length - 1) / 119;
  return Array.from({ length: 120 }, (_, i) => unique[Math.round(i * step)]);
}

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
    return matchesAttrs(p, query.attrs);
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
            points: pricePoints(prices.map((p) => p.amount)),
          }
        : null,
      // Фильтр по характеристике полезен, только если у неё есть из чего выбирать.
      attributes: [...attrMap]
        .map(([name, values]) => ({
          name,
          values: sortValues(name, [...values].map(([value, count]) => ({ value, count }))),
        }))
        .filter((a) => a.values.length > 1 && a.values.length <= 12),
      hasAvailabilityData: searched.some((p) => p.availability !== "unknown"),
      hasPopularity: searched.some((p) => (p.popularity ?? 0) > 0),
    },
  };
}

/** Работы для hero: помеченные мастерской (featured) в заданном порядке; в наличии (или с неизвестным наличием). */
export function featuredProducts(all: Product[], limit = 5): Product[] {
  return all
    .filter((p) => p.status === "active" && p.featured && p.availability !== "unavailable" && p.images.length > 0)
    .sort((a, b) => (a.featuredOrder ?? 99) - (b.featuredOrder ?? 99))
    .slice(0, limit);
}

/** Похожие: сначала из тех же подборок, затем самые новые. */
export function relatedProducts(all: Product[], product: Product, limit = 4): Product[] {
  const cats = new Set(product.categories.map((c) => c.id));
  const others = all.filter((p) => p.status === "active" && p.vkId !== product.vkId);
  const same = others.filter((p) => p.categories.some((c) => cats.has(c.id)));
  const rest = others.filter((p) => !same.includes(p));
  return [...same.sort(bySort.new), ...rest.sort(bySort.new)].slice(0, limit);
}
