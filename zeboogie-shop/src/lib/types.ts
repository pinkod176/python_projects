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

export type ProductAvailability = "in_stock" | "unavailable" | "unknown";

export type ProductAttribute = { name: string; value: string };

export type ProductOption = {
  name: string;
  values: string[];
};

export type ProductCategory = { id: string; title: string };

/** Метки на карточке. «new» вычисляется по дате публикации, «last» и «preorder» задаёт мастерская в слое curation. */
export type ProductBadge = "new" | "last" | "preorder";

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
  /** CSS object-position обложки (кадрирование 4:5 не должно резать главное). Из слоя curation. */
  focalPoint?: string;
  /** Показывать в hero на главной; порядок — featuredOrder. Из слоя curation. */
  featured?: boolean;
  featuredOrder?: number;
  /** Метки, заданные мастерской (слой curation). */
  badges: ProductBadge[];
  /** Число лайков VK, если сообщество его отдаёт. Нет данных — нет «популярных». */
  popularity?: number;
  /** Второе фото для показа при наведении в каталоге (по умолчанию — следующее после обложки). */
  hoverImage?: string;
  /** Снимки «в интерьере» (из слоя curation) — для блока на главной. */
  interior?: { url: string; note?: string }[];
  /** Обложка этой работы представляет свою подборку (плитки на главной, выпадающий «Каталог»). */
  collectionCover?: boolean;
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
  /** CSS object-position обложки подборки. */
  imageFocal?: string;
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
export type ProductCard = Pick<Product, "vkId" | "slug" | "title" | "price" | "oldPrice" | "availability"> & {
  variant?: string;
  image: string | null;
  imageWidth?: number;
  imageHeight?: number;
  /** CSS object-position обложки. */
  focalPoint?: string;
  /** Второе фото — показывается при наведении на устройствах с hover. */
  hoverImage?: string;
  categoryId?: string;
  categoryTitle?: string;
  description: string;
  badges?: ProductBadge[];
  /** У товара есть выбираемые варианты — «в корзину» с карточки заменяется переходом на страницу товара. */
  hasOptions?: boolean;
};

/** Ключ строки корзины: один товар с разными вариантами — разные строки. */
export const lineKey = (c: Pick<ProductCard, "vkId" | "variant">) => (c.variant ? `${c.vkId}|${c.variant}` : c.vkId);
