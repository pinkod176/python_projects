import { NextResponse } from "next/server";
import { z } from "zod";
import { getCatalogState } from "@/lib/catalog/service";
import { toCard } from "@/lib/catalog/query";

const body = z.object({ ids: z.array(z.string().regex(/^-?\d+_\d+$/)).max(100) });

/** Актуальные цены и доступность для позиций корзины/избранного (в браузере хранится лишь снимок). */
export async function POST(req: Request) {
  const parsed = body.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "Некорректный запрос" }, { status: 400 });
  const state = await getCatalogState();
  if (state.status !== "ok") return NextResponse.json({ error: "Каталог временно недоступен" }, { status: 503 });
  const byId = new Map(state.catalog.products.map((p) => [p.vkId, p]));
  const items = parsed.data.ids.map((id) => {
    const p = byId.get(id);
    return p && p.status === "active" ? { id, state: "ok" as const, card: toCard(p) } : { id, state: "gone" as const };
  });
  return NextResponse.json({ items }, { headers: { "Cache-Control": "no-store" } });
}
