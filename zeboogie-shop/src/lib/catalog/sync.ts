import "server-only";
import curationDemo from "@/content/curation.demo.json";
import curationLive from "@/content/curation.live.json";
import { getEnv } from "@/lib/config/env";
import { cleanCuration } from "@/lib/curation";
import { logger } from "@/lib/log";
import type { Catalog, Product, SyncResult } from "@/lib/types";
import { mapCollections, mapItem, mapShop } from "@/lib/vk/mapper";
import { getSource } from "@/lib/vk/source";
import { mergeProducts } from "./diff";
import { appendSyncLog, loadCatalog, saveCatalog } from "./store";

const log = logger("sync");

let running: Promise<SyncResult> | null = null;

/** Защита от ложного «опустошения»: пустая выдача при непустом каталоге не должна удалять всё. */
function looksSuspicious(prevActive: number, freshCount: number): boolean {
  return prevActive >= 3 && freshCount === 0;
}

/** Запуск синхронизации. Параллельные вызовы объединяются в один. */
export function runSync(): Promise<SyncResult> {
  if (!running) running = doSync().finally(() => (running = null));
  return running;
}

export const isSyncRunning = () => running !== null;

async function doSync(): Promise<SyncResult> {
  const source = getSource();
  const started = Date.now();
  const startedAt = new Date(started).toISOString();
  const base = { source: source.kind, startedAt, fetched: 0, added: 0, updated: 0, unchanged: 0, removed: 0, restored: 0, warnings: [] as string[] };
  log.info(`Синхронизация начата (источник: ${source.kind})`);
  try {
    const raw = await source.fetch();
    const previous = await loadCatalog(source.kind);
    const prevByKey = new Map((previous?.products ?? []).map((p) => [p.vkId, p]));
    const domain = getEnv().VK_PUBLIC_DOMAIN;
    const albums = new Map(raw.albums.map((a) => [a.id, a.title]));
    // Слой витрины: для демо и реального сообщества — разные файлы, они не смешиваются.
    const curation = cleanCuration(source.kind === "demo" ? curationDemo : curationLive);
    const ctx = { domain, albums, albumMembership: raw.albumMembership, nowIso: startedAt, curation };

    const fresh: Product[] = raw.items
      // Товары, удалённые на стороне VK (availability=1), не публикуем.
      .filter((i) => i.availability !== 1)
      .map((i) => mapItem(i, ctx, prevByKey.get(`${i.owner_id}_${i.id}`)));

    const prevActive = (previous?.products ?? []).filter((p) => p.status === "active").length;
    const warnings = [...raw.warnings];
    let complete = true;
    if (looksSuspicious(prevActive, fresh.length)) {
      complete = false;
      warnings.push("VK вернул пустой каталог при непустом снимке — удаление товаров пропущено.");
    }

    const diff = mergeProducts(previous?.products ?? [], fresh, startedAt, complete);
    const catalog: Catalog = {
      meta: { source: source.kind, syncedAt: startedAt, durationMs: Date.now() - started },
      shop: mapShop(raw.group, domain),
      collections: mapCollections(raw.albums, diff.products),
      products: diff.products,
    };
    await saveCatalog(catalog);

    const result: SyncResult = {
      ...base, ok: true, fetched: fresh.length, warnings, durationMs: Date.now() - started,
      added: diff.added, updated: diff.updated, unchanged: diff.unchanged, removed: diff.removed, restored: diff.restored,
    };
    await appendSyncLog(result);
    log.info("Синхронизация завершена", { ...result });
    return result;
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    const result: SyncResult = { ...base, ok: false, durationMs: Date.now() - started, error: message };
    log.error("Синхронизация не удалась", { error: message });
    await appendSyncLog(result).catch(() => undefined);
    return result;
  }
}
