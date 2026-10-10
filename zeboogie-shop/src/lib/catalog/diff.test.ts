import { describe, expect, it } from "vitest";
import { mapItem } from "@/lib/vk/mapper";
import { vkMarketItem } from "@/lib/vk/schemas";
import { mergeProducts } from "./diff";

const ctx = (t: string) => ({ domain: "vk.ru", albums: new Map<number, string>(), nowIso: t });
const mk = (id: number, price = "100", t = "t1") =>
  mapItem(vkMarketItem.parse({ id, owner_id: -1, title: `Товар ${id}`, price: { amount: price, currency: { name: "RUB" } } }), ctx(t));

describe("mergeProducts", () => {
  it("добавляет, обновляет, не дублирует", () => {
    const first = mergeProducts([], [mk(1), mk(2), mk(2)], "t1", true);
    expect(first.products).toHaveLength(2);
    expect(first.added).toBe(2);
    const second = mergeProducts(first.products, [mk(1), mk(2, "200", "t2"), mk(3, "100", "t2")], "t2", true);
    expect(second).toMatchObject({ added: 1, updated: 1, unchanged: 1, removed: 0 });
    expect(second.products).toHaveLength(3);
  });
  it("помечает исчезнувшие removed и восстанавливает вернувшиеся", () => {
    const a = mergeProducts([], [mk(1), mk(2)], "t1", true).products;
    const b = mergeProducts(a, [mk(1)], "t2", true);
    expect(b.removed).toBe(1);
    expect(b.products.find((p) => p.itemId === 2)?.status).toBe("removed");
    const c = mergeProducts(b.products, [mk(1), mk(2)], "t3", true);
    expect(c.restored).toBe(1);
    expect(c.products.find((p) => p.itemId === 2)?.status).toBe("active");
  });
  it("при неполной выгрузке ничего не удаляет", () => {
    const a = mergeProducts([], [mk(1), mk(2)], "t1", true).products;
    const b = mergeProducts(a, [], "t2", false);
    expect(b.removed).toBe(0);
    expect(b.products.every((p) => p.status === "active")).toBe(true);
  });
});
