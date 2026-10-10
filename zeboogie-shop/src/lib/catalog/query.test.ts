import { describe, expect, it } from "vitest";
import { mapItem } from "@/lib/vk/mapper";
import { vkMarketItem } from "@/lib/vk/schemas";
import { queryProducts } from "./query";

const ctx = { domain: "vk.ru", albums: new Map([[1, "Рамки"], [2, "Броши"]]), nowIso: "t" };
const mk = (id: number, title: string, price: number, album: number, date: number) =>
  mapItem(vkMarketItem.parse({ id, owner_id: -1, title, description: id === 1 ? "Ёлочка из дерева" : "", date, albums_ids: [album], price: { amount: String(price * 100), currency: { name: "RUB" } } }), ctx);
const products = [mk(1, "Рамка XS", 1000, 1, 3), mk(2, "Брошь Рыба", 800, 2, 2), mk(3, "Рамка L", 1700, 1, 1)];
const base = { sort: "new" as const, attrs: [], page: 1, pageSize: 12 };

describe("queryProducts", () => {
  it("сортирует по цене", () => {
    expect(queryProducts(products, { ...base, sort: "price-asc" }).items.map((i) => i.title)).toEqual(["Брошь Рыба", "Рамка XS", "Рамка L"]);
    expect(queryProducts(products, { ...base, sort: "price-desc" }).items[0].title).toBe("Рамка L");
  });
  it("фильтрует по подборке и цене", () => {
    expect(queryProducts(products, { ...base, category: "a1", max: 150000 }).items.map((i) => i.title)).toEqual(["Рамка XS"]);
  });
  it("ищет по названию и описанию, ё = е", () => {
    expect(queryProducts(products, { ...base, q: "рыба" }).total).toBe(1);
    expect(queryProducts(products, { ...base, q: "елочка" }).total).toBe(1);
  });
  it("не показывает индикатор наличия без данных", () => {
    expect(queryProducts(products, base).facets.hasAvailabilityData).toBe(false);
  });
  it("пагинирует", () => {
    const r = queryProducts(products, { ...base, pageSize: 2, page: 2 });
    expect(r.items).toHaveLength(1);
    expect(r.total).toBe(3);
  });
});
