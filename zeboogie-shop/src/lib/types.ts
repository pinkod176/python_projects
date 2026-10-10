/** Единый внутренний формат данных. UI знает только о нём, а не о VK API. */

export type Money = {
  /** Сумма в минимальных единицах (копейки). */
  amount: number;
  /** Код валюты ISO 4217, например RUB. */
  currency: string;
};

export type ProductImage = {
  url: string;
  width?: number;
  height?: number;
};

export type ProductAvailability = "in_stock" | "unavailable";

export type ProductAttribute = { name: string; value: string };

export type ProductOption = {
  name: string;
  values: string[];
};

export type ProductCategory = { id: string; title: string };

export type Product = {
  /** Стабильный внутренний ключ вида `-123_456` (owner_id_item_id). Используется для дедупликации. */
  vkId: string;
  itemId: number;
  ownerId: number;
  slug: string;
  title: string;
  description: string;
  price: Money | null;
  /** Предыдущая цена — только если VK вернул подтверждённую old_amount > amount. */
  oldPrice: Money | null;
  images: ProductImage[];
  categories: ProductCategory[];
  attributes: ProductAttribute[];
  /** Выбираемые варианты — только если присутствуют в исходных данных. */
  options: ProductOption[];
  availability: ProductAvailability;
  vkUrl: string;
  /** Unix-время публикации в VK (секунды). */
  publishedAt: number;
  /** removed — товар исчез из сообщества при последней полной синхронизации. */
  status: "active" | "removed";
  firstSeenAt: string;
  updatedAt: string;
  removedAt?: string;
};

export type Collection = {
  id: string;
  title: string;
  count: number;
  image?: string;
};

/** Из VK берём только товары. Здесь — минимум, нужный для ссылок на сообщество (заказ, оригинал товара). */
export type ShopInfo = {
  groupId: number;
  screenName: string;
  url: string;
  /** Ссылка на личные сообщения сообщества (оформление заказа). */
  messageUrl: string;
};

export type CatalogMeta = {
  source: "demo" | "vk";
  syncedAt: string;
  durationMs: number;
};

export type Catalog = {
  meta: CatalogMeta;
  shop: ShopInfo;
  collections: Collection[];
  products: Product[];
};

export type SyncResult = {
  ok: boolean;
  source: "demo" | "vk";
  startedAt: string;
  durationMs: number;
  fetched: number;
  added: number;
  updated: number;
  unchanged: number;
  removed: number;
  restored: number;
  warnings: string[];
  error?: string;
};

/** Облегчённый снимок товара для корзины/избранного на клиенте. */
export type ProductCard = Pick<
  Product,
  "vkId" | "slug" | "title" | "price" | "oldPrice" | "availability"
> & { image: string | null; imageWidth?: number; imageHeight?: number; categoryTitle?: string; description: string };
