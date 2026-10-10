import "server-only";
import { getEnv } from "@/lib/config/env";
import { logger } from "@/lib/log";
import { VkApiError } from "./errors";
import { vkCall } from "./client";
import { vkAlbum, vkGroup, vkMarketItem, vkMarketList, type VkAlbum, type VkGroup, type VkMarketItem } from "./schemas";
import { z } from "zod";

const log = logger("vk.api");
const PAGE = 200; // максимум для market.get

export type RawCatalog = {
  group: VkGroup;
  albums: VkAlbum[];
  items: VkMarketItem[];
  albumMembership: Map<number, number[]>;
  warnings: string[];
};

export async function getGroup(): Promise<VkGroup> {
  const res = await vkCall("groups.getById", {
    group_id: getEnv().VK_GROUP.replace(/^club|^public/, ""),
    fields: "market",
  });
  // v5.199: { groups: [...] }, старые версии: [...]
  const list = z.union([z.object({ groups: z.array(vkGroup) }).transform((o) => o.groups), z.array(vkGroup)]).parse(res);
  if (!list[0]) throw new VkApiError(`Сообщество «${getEnv().VK_GROUP}» не найдено`, 100, false);
  return list[0];
}

async function getAllPages(ownerId: number, extra: Record<string, string | number> = {}) {
  const items: VkMarketItem[] = [];
  const warnings: string[] = [];
  let offset = 0;
  let total = Infinity;
  while (offset < total) {
    const res = vkMarketList.parse(
      await vkCall("market.get", { owner_id: ownerId, count: PAGE, offset, extended: 1, ...extra }),
    );
    total = res.count;
    for (const raw of res.items) {
      const parsed = vkMarketItem.safeParse(raw);
      if (parsed.success) items.push(parsed.data);
      else warnings.push(`Пропущен товар с неожиданной структурой: ${parsed.error.issues[0]?.message ?? "?"}`);
    }
    if (!res.items.length) break;
    offset += PAGE;
    log.info(`market.get: ${Math.min(offset, total)}/${total}`);
  }
  return { items, warnings, total };
}

export async function fetchRawCatalog(): Promise<RawCatalog> {
  const group = await getGroup();
  const ownerId = -group.id;
  if (group.market?.enabled !== undefined && !group.market.enabled) {
    throw new VkApiError("В сообществе отключён раздел «Товары».", null, false);
  }

  const albumsRes = z
    .object({ count: z.number(), items: z.array(z.unknown()) })
    .parse(await vkCall("market.getAlbums", { owner_id: ownerId, count: 100 }));
  const albums = albumsRes.items.flatMap((a) => {
    const p = vkAlbum.safeParse(a);
    return p.success ? [p.data] : [];
  });

  const { items, warnings } = await getAllPages(ownerId);

  // Если товары не содержат albums_ids, определяем членство запросами по каждой подборке.
  const albumMembership = new Map<number, number[]>();
  if (albums.length && !items.some((i) => i.albums_ids?.length)) {
    for (const album of albums) {
      const { items: inAlbum } = await getAllPages(ownerId, { album_id: album.id });
      for (const it of inAlbum) albumMembership.set(it.id, [...(albumMembership.get(it.id) ?? []), album.id]);
    }
  }
  return { group, albums, items, albumMembership, warnings };
}
