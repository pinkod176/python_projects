import "server-only";
import { randomInt } from "node:crypto";
import { getEnv } from "@/lib/config/env";
import { vkCall } from "./client";

/**
 * Отправка заказа сообщением от имени сообщества. Требует ключ СООБЩЕСТВА с правом «Сообщения»,
 * а получатель должен заранее разрешить сообщения от сообщества. Иначе VK вернёт ошибку,
 * и мы честно сообщим покупателю, что автоматическая передача не удалась.
 */
export async function sendOrderMessage(text: string): Promise<void> {
  const to = getEnv().ORDER_NOTIFY_VK_USER_ID;
  await vkCall("messages.send", {
    user_id: to,
    random_id: randomInt(1, 2 ** 31 - 1),
    message: text,
  });
}
