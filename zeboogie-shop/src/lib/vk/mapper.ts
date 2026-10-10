import { makeSlug } from "@/lib/format";
import type { Collection, Product, ProductAttribute, ProductImage, ProductOption, ShopInfo } from "@/lib/types";
import type { VkAlbum, VkGroup, VkMarketItem } from "./schemas";

type PhotoSizes = { url?: string; src?: string; width?: number; height?: number }[];

/** Выбирает самый крупный вариант изображения (VK отдаёт массив sizes). */
export function bestSize(sizes: PhotoSizes | undefined): ProductImage | null {
  if (!sizes?.length) return null;
  const withUrl = sizes
    .map((s) => ({ url: s.url ?? s.src, width: s.width, height: s.height }))
    .filter((s): s is { url: string; width: number | undefined; height: number | undefined } => Boolean(s.url));
  if (!withUrl.length) return null;
  const best = withUrl.reduce((a, b) => ((b.width ?? 0) * (b.height ?? 0) > (a.width ?? 0) * (a.height ?? 0) ? b : a));
  return { url: best.url, width: best.width || undefined, height: best.height || undefined };
}

export function mapImages(item: VkMarketItem): ProductImage[] {
  const out: ProductImage[] = [];
  const seen = new Set<string>();
  for (const photo of item.photos ?? []) {
    const img = bestSize(photo.sizes);
    if (img && !seen.has(img.url)) {
      seen.add(img.url);
      out.push(img);
    }
  }
  if (!out.length && item.thumb_photo) out.push({ url: item.thumb_photo });
  return out;
}

function toMinor(v: string | number | undefined): number | null {
  if (v === undefined) return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) && n >= 0 ? Math.round(n) : null;
}

export function mapPrice(item: VkMarketItem): Pick<Product, "price" | "oldPrice"> {
  const p = item.price;
  const amount = p ? toMinor(p.amount) : null;
  if (!p || amount === null) return { price: null, oldPrice: null };
  const currency = p.currency?.name?.trim() || "RUB";
  const old = toMinor(p.old_amount);
  return {
    price: { amount, currency },
    // Старая цена показывается только если VK действительно передал её и она выше текущей.
    oldPrice: old !== null && old > amount ? { amount: old, currency } : null,
  };
}

export function mapAttributes(item: VkMarketItem): ProductAttribute[] {
  const out: ProductAttribute[] = [];
  for (const pv of item.property_values ?? []) {
    const name = (pv.property_name ?? pv.variant_name)?.trim();
    const value = (pv.value_name ?? pv.variant_value)?.trim();
    if (name && value) out.push({ name, value });
  }
  return out;
}

/** Группирует варианты по названию свойства. Если VK не вернул варианты — пустой список. */
export function mapOptions(item: VkMarketItem): ProductOption[] {
  const groups = new Map<string, Set<string>>();
  for (const v of item.variants ?? []) {
    const name = v.property_name?.trim();
    const value = (v.value ?? v.title)?.trim();
    if (!name || !value) continue;
    if (!groups.has(name)) groups.set(name, new Set());
    groups.get(name)!.add(value);
  }
  return [...groups].map(([name, values]) => ({ name, values: [...values] }));
}

export type MapContext = {
  domain: string;
  /** albumId -> название подборки. */
  albums: Map<number, string>;
  /** Если albums_ids в товарах не пришли, членство восстанавливается запросами по подборкам. */
  albumMembership?: Map<number, number[]>;
  nowIso: string;
};

export function mapItem(item: VkMarketItem, ctx: MapContext, previous?: Product): Product {
  const vkId = `${item.owner_id}_${item.id}`;
  const albumIds = item.albums_ids?.length ? item.albums_ids : (ctx.albumMembership?.get(item.id) ?? []);
  let categories = albumIds
    .filter((id) => ctx.albums.has(id))
    .map((id) => ({ id: `a${id}`, title: ctx.albums.get(id)! }));
  if (!categories.length && item.category?.name) {
    categories = [{ id: `c${item.category.id ?? item.category.name}`, title: item.category.name }];
  }
    return {
    vkId,
    itemId: item.id,
    ownerId: item.owner_id,
    // slug фиксируется при первом появлении, чтобы URL не менялись при переименовании.
    slug: previous?.slug ?? makeSlug(item.title, item.id),
    title: item.title.trim(),
    description: (item.description ?? "").trim(),
    ...mapPrice(item),
    images: mapImages(item),
    categories,
    attributes: mapAttributes(item),
    options: mapOptions(item),
    // Наличие показываем только если VK его передал.
    availability: item.availability === undefined ? "unknown" : item.availability === 0 ? "in_stock" : "unavailable",
    vkUrl: `https://${ctx.domain}/market${item.owner_id}?w=product${item.owner_id}_${item.id}`,
    publishedAt: item.date ?? 0,
    status: "active",
    firstSeenAt: previous?.firstSeenAt ?? ctx.nowIso,
    updatedAt: ctx.nowIso,
  };
}

export function mapCollections(albums: VkAlbum[], products: Product[]): Collection[] {
  return albums
    .map((a) => {
      const id = `a${a.id}`;
      const members = products.filter((p) => p.status === "active" && p.categories.some((c) => c.id === id));
      return {
        id,
        title: a.title,
        count: members.length,
        image: bestSize(a.photo?.sizes)?.url ?? members.find((m) => m.images[0])?.images[0]?.url,
      };
    })
    .filter((c) => c.count > 0);
}

export function mapShop(group: VkGroup, domain: string): ShopInfo {
  const screenName = group.screen_name ?? `club${group.id}`;
  return {
    groupId: group.id,
    screenName,
    url: `https://${domain}/${screenName}`,
    messageUrl: `https://${domain}/write-${group.id}`,
  };
}

/** Содержимое «снимка» для сравнения: без служебных временных меток. */
export function fingerprint(p: Product): string {
  const { updatedAt, firstSeenAt, removedAt, ...rest } = p;
  void updatedAt; void firstSeenAt; void removedAt;
  return JSON.stringify(rest);
}
