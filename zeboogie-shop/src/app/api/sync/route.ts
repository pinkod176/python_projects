import { timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import { getEnv } from "@/lib/config/env";
import { runSync } from "@/lib/catalog/sync";

export const maxDuration = 300;

function authorized(header: string | null, secret: string): boolean {
  const given = Buffer.from(header?.replace(/^Bearer\s+/i, "") ?? "");
  const expected = Buffer.from(secret);
  return given.length === expected.length && timingSafeEqual(given, expected);
}

/** Запуск синхронизации по расписанию: `curl -X POST -H "Authorization: Bearer $SYNC_SECRET" …/api/sync` */
export async function POST(req: Request) {
  const { SYNC_SECRET } = getEnv();
  if (!SYNC_SECRET) return NextResponse.json({ error: "SYNC_SECRET не настроен" }, { status: 503 });
  if (!authorized(req.headers.get("authorization"), SYNC_SECRET)) {
    return NextResponse.json({ error: "Нет доступа" }, { status: 401 });
  }
  const result = await runSync();
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
