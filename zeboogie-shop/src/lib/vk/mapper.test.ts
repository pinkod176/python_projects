import { describe, expect, it } from "vitest";
import { mapItem, mapPrice, bestSize } from "./mapper";
import { vkMarketItem } from "./schemas";

const ctx = { domain: "vk.ru", albums: new Map([[1, "Рамки"]]), nowIso: "2026-01-01T00:00:00.000Z" };
const item = (extra: object = {}) =>
  vkMarketItem.parse({ id: 5, owner_id: -10, title: "Рамка М", price: { amount: "90000", currency: { name: "RUB" } }, ...extra });

describe("VK mapper", () => {
  it("переводит копейки и не придумывает старую цену", () => {
    expect(mapPrice(item()).price).toEqual({ amount: 90000, currency: "RUB" });
    expect(mapPrice(item()).oldPrice).toBeNull();
  });
  it("показывает старую цену только если она выше текущей", () => {
    const base = { price: { amount: "90000", old_amount: "120000", currency: { name: "RUB" } } };
    expect(mapPrice(item(base)).oldPrice?.amount).toBe(120000);
    expect(mapPrice(item({ price: { ...base.price, old_amount: "50000" } })).oldPrice).toBeNull();
  });
  it("наличие неизвестно, если VK его не передал", () => {
    expect(mapItem(item(), ctx).availability).toBe("unknown");
    expect(mapItem(item({ availability: 0 }), ctx).availability).toBe("in_stock");
    expect(mapItem(item({ availability: 2 }), ctx).availability).toBe("unavailable");
  });
  it("формирует стабильный ключ и сохраняет slug при переименовании", () => {
    const first = mapItem(item(), ctx);
    expect(first.vkId).toBe("-10_5");
    expect(first.slug).toBe("ramka-m-5");
    const renamed = mapItem(item({ title: "Совсем другое" }), ctx, first);
    expect(renamed.slug).toBe("ramka-m-5");
  });
  it("берёт самую крупную фотографию", () => {
    expect(bestSize([{ url: "a", width: 10, height: 10 }, { url: "b", width: 100, height: 100 }])?.url).toBe("b");
  });
  it("варианты появляются только из данных", () => {
    expect(mapItem(item(), ctx).options).toEqual([]);
    const v = mapItem(item({ variants: [{ property_name: "Цвет", value: "Белый" }, { property_name: "Цвет", value: "Серый" }] }), ctx);
    expect(v.options).toEqual([{ name: "Цвет", values: ["Белый", "Серый"] }]);
  });
});
