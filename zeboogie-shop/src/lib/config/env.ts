import "server-only";
import { z } from "zod";

const schema = z.object({
  VK_MODE: z.enum(["demo", "live"]).default("demo"),
  VK_GROUP: z.string().min(1).default("zeboogie"),
  VK_ACCESS_TOKEN: z.string().optional().default(""),
  VK_API_VERSION: z.string().default("5.199"),
  VK_API_BASE: z.url().default("https://api.vk.com/method"),
  VK_PUBLIC_DOMAIN: z.string().default("vk.ru"),
  SYNC_SECRET: z.string().optional().default(""),
  SYNC_TTL_MINUTES: z.coerce.number().int().min(1).default(30),
  DATA_DIR: z.string().default("./data"),
  ORDER_NOTIFY_VK_USER_ID: z.string().optional().default(""),
  SITE_URL: z.url().default("http://localhost:3000"),
  SHOP_NAME: z.string().default("Zeboogie"),
  SHOP_EMAIL: z.string().optional().default(""),
  SHOP_PHONE: z.string().optional().default(""),
});

export type Env = z.infer<typeof schema>;

let cached: Env | null = null;

/** Серверная конфигурация. Секреты (VK_ACCESS_TOKEN, SYNC_SECRET) никогда не попадают в клиент. */
export function getEnv(): Env {
  if (!cached) {
    const parsed = schema.safeParse(process.env);
    if (!parsed.success) {
      throw new Error(`Некорректные переменные окружения: ${z.prettifyError(parsed.error)}`);
    }
    cached = parsed.data;
  }
  return cached;
}

export const isDemo = () => getEnv().VK_MODE === "demo";
