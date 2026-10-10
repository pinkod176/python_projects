import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Проверка «живого» пути VK на подменённом fetch (реальный VK в CI недоступен):
 * пагинация по 200, повтор при лимите запросов (код 6), ошибка авторизации (код 5),
 * пометка исчезнувших товаров и защита от пустой выдачи.
 */
const GROUP = 777;
const item = (id: number) => ({
  id, owner_id: -GROUP, title: `Товар ${id}`, description: "",
  price: { amount: "150000", currency: { name: "RUB" } }, availability: 0, date: 1700000000 + id,
  photos: [{ sizes: [{ url: `https://sun1.userapi.com/${id}.jpg`, width: 800, height: 1000 }] }], albums_ids: [5],
});

let total = 250;
let rateLimitOnce = true;
let authFail = false;
let emptyMarket = false;
const calls: string[] = [];

function fakeFetch(url: string | URL | Request, init?: RequestInit) {
  const method = String(url).split("/method/")[1];
  const body = new URLSearchParams(String(init?.body));
  calls.push(method);
  const ok = (response: unknown) => new Response(JSON.stringify({ response }));
  const fail = (code: number, msg: string) => new Response(JSON.stringify({ error: { error_code: code, error_msg: msg } }));
  if (authFail) return Promise.resolve(fail(5, "User authorization failed"));
  switch (method) {
    case "groups.getById": return Promise.resolve(ok({ groups: [{ id: GROUP, name: "x", screen_name: "zeboogie", market: { enabled: 1 } }] }));
    case "market.getAlbums": return Promise.resolve(ok({ count: 1, items: [{ id: 5, title: "Рамки", count: total }] }));
    case "market.get": {
      if (rateLimitOnce) { rateLimitOnce = false; return Promise.resolve(fail(6, "Too many requests per second")); }
      const offset = Number(body.get("offset"));
      const count = emptyMarket ? 0 : total;
      const items = Array.from({ length: Math.max(0, Math.min(200, count - offset)) }, (_, i) => item(offset + i + 1));
      return Promise.resolve(ok({ count, items }));
    }
  }
  return Promise.resolve(fail(100, "unknown method"));
}

describe("живая синхронизация VK (подмена fetch)", () => {
  let dir: string;
  beforeEach(() => {
    vi.resetModules();
    dir = mkdtempSync(path.join(tmpdir(), "zb-"));
    vi.stubEnv("VK_MODE", "live");
    vi.stubEnv("VK_ACCESS_TOKEN", "SECRET-TOKEN-123");
    vi.stubEnv("DATA_DIR", dir);
    vi.stubGlobal("fetch", vi.fn(fakeFetch));
    total = 250; rateLimitOnce = true; authFail = false; emptyMarket = false; calls.length = 0;
  });
  afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

  it("загружает весь каталог постранично, переживает лимит запросов, потом удаляет исчезнувшие", async () => {
    const { runSync } = await import("@/lib/catalog/sync");
    const first = await runSync();
    expect(first).toMatchObject({ ok: true, source: "vk", fetched: 250, added: 250 });
    expect(calls.filter((c) => c === "market.get")).toHaveLength(3); // 1 неудачный (код 6) + 2 страницы

    total = 249;
    const second = await runSync();
    expect(second).toMatchObject({ ok: true, added: 0, removed: 1, unchanged: 249 });
    const snap = JSON.parse(readFileSync(path.join(dir, "catalog.vk.json"), "utf8"));
    expect(snap.products.find((p: { itemId: number }) => p.itemId === 250).status).toBe("removed");
    expect(snap.products).toHaveLength(250); // дублей нет
  });

  it("ошибка авторизации: sync честно падает, снимок сохраняется, токен не попадает в лог", async () => {
    const { runSync } = await import("@/lib/catalog/sync");
    await runSync();
    authFail = true;
    const res = await runSync();
    expect(res.ok).toBe(false);
    expect(res.error).toContain("[5]");
    expect(JSON.stringify(res)).not.toContain("SECRET-TOKEN-123");
    const snap = JSON.parse(readFileSync(path.join(dir, "catalog.vk.json"), "utf8"));
    expect(snap.products.filter((p: { status: string }) => p.status === "active")).toHaveLength(250);
  });

  it("пустая выдача при непустом каталоге не стирает товары", async () => {
    const { runSync } = await import("@/lib/catalog/sync");
    await runSync();
    emptyMarket = true;
    const res = await runSync();
    expect(res.ok).toBe(true);
    expect(res.removed).toBe(0);
    expect(res.warnings.join(" ")).toContain("пропущено");
  });

  it("без токена — понятная ошибка", async () => {
    vi.stubEnv("VK_ACCESS_TOKEN", "");
    const { runSync } = await import("@/lib/catalog/sync");
    const res = await runSync();
    expect(res.ok).toBe(false);
    expect(res.error).toContain("VK_ACCESS_TOKEN");
  });
});
