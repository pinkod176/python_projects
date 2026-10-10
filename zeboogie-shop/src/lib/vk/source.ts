import "server-only";
import { readFile } from "node:fs/promises";
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
const demoSource: CatalogSource = {
  kind: "demo",
  async fetch() {
    const file = path.join(process.cwd(), "src/lib/vk/demo/market.json");
    const data = demoFile.parse(JSON.parse(await readFile(file, "utf8")));
    return { ...data, albumMembership: new Map(), warnings: [] };
  },
};

const vkSource: CatalogSource = { kind: "vk", fetch: fetchRawCatalog };

export function getSource(): CatalogSource {
  return isDemo() ? demoSource : vkSource;
}
