import { NextResponse } from "next/server";
import { z } from "zod";
import { queryProducts, SORTS } from "@/lib/catalog/query";
import { getCatalogState } from "@/lib/catalog/service";

const params = z.object({
  q: z.string().max(100).optional(),
  category: z.string().max(40).optional(),
  sort: z.enum(SORTS).default("new"),
  min: z.coerce.number().int().min(0).optional(),
  max: z.coerce.number().int().min(0).optional(),
  inStock: z.enum(["1", "0"]).optional(),
  attr: z.array(z.string().max(160)).default([]),
  page: z.coerce.number().int().min(1).max(500).default(1),
  pageSize: z.coerce.number().int().min(1).max(48).default(12),
});

export async function GET(req: Request) {
  const sp = new URL(req.url).searchParams;
  const parsed = params.safeParse({
    q: sp.get("q") || undefined,
    category: sp.get("category") || undefined,
    sort: sp.get("sort") || undefined,
    min: sp.get("min") || undefined,
    max: sp.get("max") || undefined,
    inStock: sp.get("inStock") || undefined,
    attr: sp.getAll("attr"),
    page: sp.get("page") || undefined,
    pageSize: sp.get("pageSize") || undefined,
  });
  if (!parsed.success) return NextResponse.json({ error: "Некорректные параметры" }, { status: 400 });

  const state = await getCatalogState();
  if (state.status !== "ok") return NextResponse.json({ error: "Каталог временно недоступен" }, { status: 503 });

  const { attr, inStock, ...rest } = parsed.data;
  return NextResponse.json(queryProducts(state.catalog.products, { ...rest, attrs: attr, inStock: inStock === "1" }), {
    headers: { "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300" },
  });
}
