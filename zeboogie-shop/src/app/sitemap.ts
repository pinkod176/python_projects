import type { MetadataRoute } from "next";
import { getCatalogState } from "@/lib/catalog/service";
import { getEnv, isDemo } from "@/lib/config/env";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Тестовые товары не публикуем в sitemap.
  if (isDemo()) return [];
  const site = getEnv().SITE_URL;
  const state = await getCatalogState();
  const pages: MetadataRoute.Sitemap = [{ url: site }, { url: `${site}/catalog` }, { url: `${site}/about` }, { url: `${site}/delivery` }, { url: `${site}/contacts` }];
  if (state.status !== "ok") return pages;
  return [
    ...pages,
    ...state.catalog.collections.map((c) => ({ url: `${site}/catalog?category=${c.id}` })),
    ...state.catalog.products
      .filter((p) => p.status === "active")
      .map((p) => ({ url: `${site}/product/${p.slug}`, lastModified: p.updatedAt })),
  ];
}
