import { NextResponse } from "next/server";
import { queryProducts } from "@/lib/catalog/query";
import { getCatalogState } from "@/lib/catalog/service";
import { normalizeText } from "@/lib/format";
import type { Collection, ProductCard } from "@/lib/types";

export type SearchSuggestions = {
  products: ProductCard[];
  /** Сколько работ нашлось всего (подсказки показывают не больше шести). */
  total: number;
  categories: Pick<Collection, "id" | "title" | "count" | "image" | "imageFocal">[];
};

/** Подсказки поиска: работы с фото и подходящие подборки. Данные берутся из снимка каталога, а не из VK. */
export async function GET(req: Request) {
  const q = (new URL(req.url).searchParams.get("q") ?? "").slice(0, 100);
  const tokens = normalizeText(q).split(" ").filter(Boolean);
  if (!tokens.length) return NextResponse.json({ products: [], total: 0, categories: [] } satisfies SearchSuggestions);

  const state = await getCatalogState();
  if (state.status !== "ok") return NextResponse.json({ error: "Каталог временно недоступен" }, { status: 503 });

  const found = queryProducts(state.catalog.products, { q, sort: "new", attrs: [], page: 1, pageSize: 6 });
  const categories = state.catalog.collections
    .filter((c) => tokens.every((t) => normalizeText(c.title).includes(t)))
    .slice(0, 3)
    .map(({ id, title, count, image, imageFocal }) => ({ id, title, count, image, imageFocal }));

  return NextResponse.json({ products: found.items, total: found.total, categories } satisfies SearchSuggestions, {
    headers: { "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300" },
  });
}
