import "server-only";
import { cache } from "react";
import { getEnv } from "@/lib/config/env";
import { logger } from "@/lib/log";
import type { Catalog, Product } from "@/lib/types";
import { getSource } from "@/lib/vk/source";
import { stat } from "node:fs/promises";
import path from "node:path";
import { loadCatalog } from "./store";
import { isSyncRunning, runSync } from "./sync";
import { itemIdFromSlug } from "@/lib/format";

const log = logger("catalog");

export type CatalogState =
  | { status: "ok"; catalog: Catalog; stale: boolean }
  | { status: "error"; message: string };

/**
 * Единая точка чтения каталога для UI. Страницы не обращаются к VK:
 *  1) читаем снимок из хранилища;
 *  2) если снимка нет — первоначальная загрузка (ожидаем её);
 *  3) если снимок старше SYNC_TTL_MINUTES — обновляем в фоне, отдавая старые данные (stale-while-revalidate).
 */
export const getCatalogState = cache(async (): Promise<CatalogState> => {
  const source = getSource().kind;
  let catalog = await loadCatalog(source);

  if (!catalog) {
    log.info("Снимка нет — первоначальная загрузка каталога");
    const result = await runSync();
    if (!result.ok) return { status: "error", message: result.error ?? "Не удалось загрузить каталог" };
    catalog = await loadCatalog(source);
    if (!catalog) return { status: "error", message: "Каталог не сохранился" };
    return { status: "ok", catalog, stale: false };
  }

  // Демо-данные статичны, но при правке файлов демо (json/фото) снимок пересобирается сам.
  if (source === "demo" && (await demoFilesChangedSince(catalog.meta.syncedAt)) && !isSyncRunning()) {
    const result = await runSync();
    const fresh = result.ok ? await loadCatalog(source) : null;
    if (fresh) return { status: "ok", catalog: fresh, stale: false };
  }

  const ageMs = Date.now() - new Date(catalog.meta.syncedAt).getTime();
  const stale = ageMs > getEnv().SYNC_TTL_MINUTES * 60_000;
  if (stale && !isSyncRunning() && source === "vk") {
    void runSync(); // демо-данные статичны, обновлять их по таймеру незачем
  }
  return { status: "ok", catalog, stale };
});

export async function findProductBySlug(slug: string): Promise<{ catalog: Catalog; product: Product } | null> {
  const state = await getCatalogState();
  if (state.status !== "ok") return null;
  const id = itemIdFromSlug(slug);
  const product = state.catalog.products.find((p) => p.itemId === id);
  return product ? { catalog: state.catalog, product } : null;
}

async function demoFilesChangedSince(iso: string): Promise<boolean> {
  const base = process.cwd();
  const since = new Date(iso).getTime();
  const paths = [
    path.join(/* turbopackIgnore: true */ base, "src/lib/vk/demo/market.json"),
    path.join(/* turbopackIgnore: true */ base, "public/demo/products"),
  ];
  const times = await Promise.all(paths.map((p) => stat(p).then((s) => s.mtimeMs).catch(() => 0)));
  return times.some((t) => t > since);
}
