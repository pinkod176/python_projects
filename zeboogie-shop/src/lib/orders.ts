import { z } from "zod";
import { formatMoney } from "./format";
import type { Product } from "./types";

export const orderRequestSchema = z.object({
  customer: z.object({
    name: z.string().trim().min(2, "Укажите имя").max(80),
    phone: z
      .string()
      .trim()
      .regex(/^[+\d][\d\s()\-]{6,20}$/, "Укажите телефон в формате +7 900 000-00-00"),
    city: z.string().trim().max(80).optional().default(""),
    comment: z.string().trim().max(1000).optional().default(""),
  }),
  items: z
    .array(z.object({ vkId: z.string().regex(/^-?\d+_\d+$/), variant: z.string().max(120).optional(), qty: z.number().int().min(1).max(99) }))
    .min(1, "Корзина пуста")
    .max(50),
});
export type OrderRequest = z.infer<typeof orderRequestSchema>;

export type ValidatedLine = { product: Product; qty: number; variant?: string };

export function buildOrderText(order: OrderRequest, lines: ValidatedLine[], shopName: string): string {
  const currency = lines.find((l) => l.product.price)?.product.price?.currency ?? "RUB";
  const total = lines.reduce((s, l) => s + (l.product.price?.amount ?? 0) * l.qty, 0);
  const rows = lines.map(
    (l, i) =>
      `${i + 1}. ${l.product.title}${l.variant ? ` (${l.variant})` : ""} — ${l.qty} шт.${l.product.price ? ` × ${formatMoney(l.product.price)}` : ""}\n   ${l.product.vkUrl}`,
  );
  return [
    `Заказ с сайта ${shopName}`,
    "",
    ...rows,
    "",
    `Итого: ${formatMoney({ amount: total, currency })}`,
    "",
    `Имя: ${order.customer.name}`,
    `Телефон: ${order.customer.phone}`,
    order.customer.city ? `Город: ${order.customer.city}` : "",
    order.customer.comment ? `Комментарий: ${order.customer.comment}` : "",
  ]
    .filter((l, i, a) => l !== "" || a[i - 1] !== "")
    .join("\n");
}
