import "server-only";
import { appendFile, mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { getEnv } from "@/lib/config/env";
import type { Catalog, SyncResult } from "@/lib/types";

/**
 * Файловое хранилище снимка каталога. Для демо и реального режима используются РАЗНЫЕ файлы,
 * поэтому тестовые товары никогда не смешиваются с настоящими.
 * Интерфейс узкий (load/save) — при необходимости заменяется на PostgreSQL/Prisma без изменения остального кода.
 */
const dir = () => path.resolve(process.cwd(), getEnv().DATA_DIR);
const fileFor = (source: "demo" | "vk") => path.join(dir(), `catalog.${source}.json`);

let memo: { source: string; mtimeKey: string; value: Catalog } | null = null;

export async function loadCatalog(source: "demo" | "vk"): Promise<Catalog | null> {
  if (memo && memo.source === source) return memo.value;
  try {
    const value = JSON.parse(await readFile(fileFor(source), "utf8")) as Catalog;
    memo = { source, mtimeKey: value.meta.syncedAt, value };
    return value;
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw e;
  }
}

export async function saveCatalog(catalog: Catalog): Promise<void> {
  await mkdir(dir(), { recursive: true });
  const target = fileFor(catalog.meta.source);
  const tmp = `${target}.tmp`;
  await writeFile(tmp, JSON.stringify(catalog), "utf8");
  await rename(tmp, target); // атомарная замена — читатели не увидят «половину» файла
  memo = { source: catalog.meta.source, mtimeKey: catalog.meta.syncedAt, value: catalog };
}

export async function appendSyncLog(result: SyncResult): Promise<void> {
  await mkdir(dir(), { recursive: true });
  await appendFile(path.join(dir(), "sync-log.jsonl"), JSON.stringify(result) + "\n", "utf8");
}

export async function readSyncLog(limit = 20): Promise<SyncResult[]> {
  try {
    const lines = (await readFile(path.join(dir(), "sync-log.jsonl"), "utf8")).trim().split("\n");
    return lines.slice(-limit).map((l) => JSON.parse(l) as SyncResult).reverse();
  } catch {
    return [];
  }
}
