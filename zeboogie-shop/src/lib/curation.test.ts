import { describe, expect, it } from "vitest";
import { applyCover, cleanCuration, pickHover } from "./curation";
import { deriveFormat } from "./format";
import { mapItem } from "./vk/mapper";
import { vkMarketItem } from "./vk/schemas";
import { cardBadges, featuredProducts, queryProducts, toCard } from "./catalog/query";

const imgs = ["a", "b", "c", "d"].map((u) => ({ url: u }));

describe("слой витрины (curation)", () => {
  it("ставит обложку первой, остальные фото сохраняют порядок", () => {
    expect(applyCover(imgs, 3).map((i) => i.url)).toEqual(["c", "a", "b", "d"]);
  });
  it("игнорирует некорректный номер обложки и не меняет исходный массив", () => {
    expect(applyCover(imgs, 9)).toBe(imgs);
    expect(applyCover(imgs, 0)).toBe(imgs);
    expect(applyCover(imgs, 1)).toBe(imgs);
    applyCover(imgs, 2);
    expect(imgs.map((i) => i.url)).toEqual(["a", "b", "c", "d"]);
  });
  it("второе фото для наведения: выбранное мастерской или следующее после обложки", () => {
    const ordered = applyCover(imgs, 3);
    expect(pickHover(imgs, ordered, 4)).toBe("d");
    expect(pickHover(imgs, ordered, 3)).toBe("a"); // совпало с обложкой → следующее
    expect(pickHover(imgs, ordered)).toBe("a");
  });
  it("убирает служебные ключи", () => {
    expect(cleanCuration({ _readme: "x", "2001": { cover: 2 } })).toEqual({ "2001": { cover: 2 } });
    expect(cleanCuration(null)).toEqual({});
  });
});

describe("формат из названия", () => {
  it("разбирает размеры мастерской, кириллическая «М» = M", () => {
    expect(deriveFormat("Рамка XS")).toBe("XS");
    expect(deriveFormat("Рама XL")).toBe("XL");
    expect(deriveFormat("Рамка-полка широкая XXL")).toBe("XXL");
    expect(deriveFormat("Рамка М")).toBe("M");
    expect(deriveFormat("Рамка L")).toBe("L");
    expect(deriveFormat("Рамка М 3*3")).toBe("M");
  });
  it("не придумывает размер там, где его нет", () => {
    expect(deriveFormat("Брошь Рыба")).toBeNull();
    expect(deriveFormat("Корпоративница")).toBeNull();
    expect(deriveFormat("Арт объект Золотое Сечение")).toBeNull();
  });
});

const ctx = { domain: "vk.ru", albums: new Map([[1, "Рамки"]]), nowIso: "t" };
const mk = (id: number, title: string, date: number, extra: object = {}, cur?: object) =>
  mapItem(
    vkMarketItem.parse({
      id, owner_id: -1, title, date, albums_ids: [1],
      price: { amount: String(id * 10000), currency: { name: "RUB" } },
      photos: [1, 2, 3].map((n) => ({ id: n, sizes: [{ url: `https://x/${id}-${n}.jpg`, width: 540, height: 720, type: "x" }] })),
      ...extra,
    }),
    { ...ctx, curation: cur ? { [String(id)]: cur } : undefined },
  );

describe("витрина в данных товара", () => {
  const now = 1_800_000_000;
  it("обложка, фокус и hero применяются при сборке товара", () => {
    const p = mk(1, "Рамка XS", now, {}, { cover: 2, hover: 3, focalPoint: "50% 30%", featured: true, featuredOrder: 2 });
    expect(p.images[0].url).toBe("https://x/1-2.jpg");
    expect(p.hoverImage).toBe("https://x/1-3.jpg");
    expect(p.focalPoint).toBe("50% 30%");
    expect(p.attributes).toContainEqual({ name: "Формат", value: "XS" });
    const c = toCard(p);
    expect(c.image).toBe("https://x/1-2.jpg");
    expect(c.hoverImage).toBe("https://x/1-3.jpg");
  });
  it("без записи в curation порядок фото не меняется", () => {
    const p = mk(2, "Брошь", now);
    expect(p.images.map((i) => i.url)).toEqual(["https://x/2-1.jpg", "https://x/2-2.jpg", "https://x/2-3.jpg"]);
    expect(p.featured).toBeUndefined();
  });
  it("«Новинка» — только по дате публикации (30 дней); «Последний экземпляр» — только от мастерской", () => {
    const fresh = mk(3, "Свежая", now - 5 * 86400, {}, { badges: ["last"] });
    const old = mk(4, "Старая", now - 90 * 86400);
    expect(cardBadges(fresh, now).sort()).toEqual(["last", "new"]);
    expect(cardBadges(old, now)).toEqual([]);
  });
  it("hero берёт только отмеченные работы по featuredOrder", () => {
    const list = [
      mk(5, "Третья", now, {}, { featured: true, featuredOrder: 3 }),
      mk(6, "Первая", now, {}, { featured: true, featuredOrder: 1 }),
      mk(7, "Обычная", now),
      mk(8, "Нет в наличии", now, { availability: 2 }, { featured: true, featuredOrder: 2 }),
    ];
    expect(featuredProducts(list, 5).map((p) => p.title)).toEqual(["Первая", "Третья"]);
  });
  it("«Популярные» без лайков VK = выбор мастерской; с лайками — по ним", () => {
    const a = mk(9, "А", now - 100, {}, { featured: true, featuredOrder: 1 });
    const b = mk(10, "Б", now);
    const base = { sort: "popular" as const, attrs: [], page: 1, pageSize: 12 };
    const noLikes = queryProducts([a, b], base);
    expect(noLikes.facets.hasPopularity).toBe(false);
    expect(noLikes.items.map((i) => i.title)).toEqual(["А", "Б"]);
    const liked = queryProducts([a, mk(11, "В", now, { likes: { count: 7 } })], base);
    expect(liked.facets.hasPopularity).toBe(true);
    expect(liked.items[0].title).toBe("В");
  });
  it("фильтр «Формат»: значения одной группы складываются через «или», порядок — по размерам", () => {
    const list = [mk(12, "Рамка M", now), mk(13, "Рамка S", now), mk(14, "Рамка XL", now), mk(15, "Брошь", now)];
    const r = queryProducts(list, { sort: "new", attrs: ["Формат:S", "Формат:M"], page: 1, pageSize: 12 });
    expect(r.items.map((i) => i.title).sort()).toEqual(["Рамка M", "Рамка S"]);
    expect(r.facets.attributes[0].values.map((v) => v.value)).toEqual(["S", "M", "XL"]);
  });
  it("ползунок цены шагает по реальным ценам", () => {
    const r = queryProducts([mk(16, "А", now), mk(17, "Б", now), mk(18, "В", now)], { sort: "new", attrs: [], page: 1, pageSize: 12 });
    expect(r.facets.price?.points).toEqual([160000, 170000, 180000]);
  });
});
