import type { Product } from "@/lib/types";
import { fingerprint } from "@/lib/vk/mapper";

export type DiffResult = {
  products: Product[];
  added: number;
  updated: number;
  unchanged: number;
  removed: number;
  restored: number;
};

/**
 * Объединяет свежие товары с предыдущим снимком.
 *  - ключ — vkId (owner_id_item_id): дубли невозможны;
 *  - новые добавляются, изменённые обновляются;
 *  - исчезнувшие из выдачи помечаются removed (а не стираются) — чтобы старые ссылки не вели в никуда;
 *  - вернувшиеся восстанавливаются.
 * `complete=false` значит, что выгрузка неполная — тогда ничего не помечается удалённым.
 */
export function mergeProducts(
  previous: Product[],
  fresh: Product[],
  nowIso: string,
  complete: boolean,
): DiffResult {
  const prev = new Map(previous.map((p) => [p.vkId, p]));
  const seen = new Set<string>();
  const out: Product[] = [];
  let added = 0, updated = 0, unchanged = 0, restored = 0, removed = 0;

  for (const p of fresh) {
    if (seen.has(p.vkId)) continue; // дубль в самой выдаче
    seen.add(p.vkId);
    const old = prev.get(p.vkId);
    if (!old) {
      added++;
      out.push(p);
    } else if (old.status === "removed") {
      restored++;
      out.push(p);
    } else if (fingerprint(old) === fingerprint(p)) {
      unchanged++;
      out.push(old);
    } else {
      updated++;
      out.push(p);
    }
  }

  for (const old of previous) {
    if (seen.has(old.vkId)) continue;
    if (old.status === "removed") {
      out.push(old);
    } else if (complete) {
      removed++;
      out.push({ ...old, status: "removed", removedAt: nowIso, updatedAt: nowIso });
    } else {
      out.push(old);
    }
  }
  return { products: out, added, updated, unchanged, removed, restored };
}
