import "server-only";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { z } from "zod";
import { isDemo } from "@/lib/config/env";
import { fetchRawCatalog, type RawCatalog } from "./api";
import { vkAlbum, vkGroup, vkMarketItem } from "./schemas";

export type CatalogSource = { kind: "demo" | "vk"; fetch(): Promise<RawCatalog> };

const demoFile = z.object({
  group: vkGroup,
  albums: z.array(vkAlbum),
  items: z.array(vkMarketItem),
});

/** ДЕМО: тестовые данные в формате ответов VK API (src/lib/vk/demo/market.json). */
/**
 * Если рядом с временной вырезкой лежат настоящие фото `public/demo/products/NN-1.jpg, NN-2.jpg…`
 * (NN = id товара − 2000), они подставляются вместо вырезки. Только для демо-режима.
 */
async function applyDemoPhotos(items: z.infer<typeof demoFile>["items"]) {
  const dir = path.join(/* turbopackIgnore: true */ process.cwd(), "public/demo/products");
  const files = await readdir(dir).catch(() => [] as string[]);
  for (const item of items) {
    const nn = String(item.id - 2000).padStart(2, "0");
    const real = files.filter((f) => new RegExp(`^${nn}-\\d+\\.jpg$`).test(f)).sort();
    if (real.length) {
      item.photos = real.map((f, i) => ({ id: item.id * 10 + i + 1, sizes: [{ url: `/demo/products/${f}` }] }));
      item.thumb_photo = `/demo/products/${real[0]}`;
    }
  }
}

const demoSource: CatalogSource = {
  kind: "demo",
  async fetch() {
    const file = path.join(/* turbopackIgnore: true */ process.cwd(), "src/lib/vk/demo/market.json");
    const data = demoFile.parse(JSON.parse(await readFile(file, "utf8")));
    await applyDemoPhotos(data.items);
    return { ...data, albumMembership: new Map(), warnings: [] };
  },
};

const vkSource: CatalogSource = { kind: "vk", fetch: fetchRawCatalog };

export function getSource(): CatalogSource {
  return isDemo() ? demoSource : vkSource;
}
