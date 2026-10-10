import { NextResponse } from "next/server";
import { getEnv, isDemo } from "@/lib/config/env";
import { getCatalogState } from "@/lib/catalog/service";
import { logger } from "@/lib/log";
import { buildOrderText, orderRequestSchema, type ValidatedLine } from "@/lib/orders";
import { sendOrderMessage } from "@/lib/vk/messages";

const log = logger("order");

/**
 * Подготовка заказа. Сайт НЕ сообщает об успешной передаче, пока заказ реально не доставлен:
 *  - delivered=true  — сообщение отправлено сообществом через VK API (нужен ORDER_NOTIFY_VK_USER_ID и ключ сообщества);
 *  - delivered=false — готов текст заказа; покупатель отправляет его сообщением в сообщество (ссылка в ответе).
 */
export async function POST(req: Request) {
  const parsed = orderRequestSchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json(
      { error: "Проверьте данные заказа", fields: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }
  const state = await getCatalogState();
  if (state.status !== "ok") return NextResponse.json({ error: "Каталог временно недоступен" }, { status: 503 });

  const byId = new Map(state.catalog.products.map((p) => [p.vkId, p]));
  const lines: ValidatedLine[] = [];
  const problems: { vkId: string; reason: "gone" | "unavailable" }[] = [];
  for (const it of parsed.data.items) {
    const product = byId.get(it.vkId);
    if (!product || product.status !== "active") problems.push({ vkId: it.vkId, reason: "gone" });
    else if (product.availability === "unavailable") problems.push({ vkId: it.vkId, reason: "unavailable" });
    else lines.push({ product, qty: it.qty, variant: it.variant });
  }
  if (problems.length) {
    return NextResponse.json({ error: "Некоторые товары больше недоступны", problems }, { status: 409 });
  }

  const env = getEnv();
  const text = buildOrderText(parsed.data, lines, env.SHOP_NAME);
  const messageUrl = state.catalog.shop.messageUrl;

  let delivered = false;
  if (!isDemo() && env.ORDER_NOTIFY_VK_USER_ID) {
    try {
      await sendOrderMessage(text);
      delivered = true;
    } catch (e) {
      log.error("Не удалось отправить заказ через VK", { error: e instanceof Error ? e.message : String(e) });
    }
  }
  return NextResponse.json({ delivered, text, messageUrl, demo: isDemo() });
}
