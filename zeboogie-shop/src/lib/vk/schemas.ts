import { z } from "zod";

/** Схемы ответов VK API. Намеренно «терпимые»: неизвестные поля пропускаются, необязательные — optional. */

const photoSize = z.object({
  url: z.string().optional(),
  src: z.string().optional(),
  width: z.number().optional(),
  height: z.number().optional(),
  type: z.string().optional(),
});

export const vkPhoto = z.object({
  id: z.number().optional(),
  sizes: z.array(photoSize).optional().default([]),
});

export const vkPrice = z.object({
  amount: z.union([z.string(), z.number()]),
  old_amount: z.union([z.string(), z.number()]).optional(),
  currency: z.object({ id: z.number().optional(), name: z.string().optional() }).optional(),
  text: z.string().optional(),
  discount_rate: z.number().optional(),
});

export const vkMarketItem = z.object({
  id: z.number(),
  owner_id: z.number(),
  title: z.string(),
  description: z.string().optional().default(""),
  price: vkPrice.optional(),
  category: z
    .object({
      id: z.number().optional(),
      name: z.string().optional(),
      section: z.object({ id: z.number().optional(), name: z.string().optional() }).optional(),
    })
    .optional(),
  thumb_photo: z.string().optional(),
  date: z.number().optional(),
  /** 0 — товар доступен, 1 — удалён, 2 — недоступен. */
  availability: z.number().optional(),
  photos: z.array(vkPhoto).optional(),
  albums_ids: z.array(z.number()).optional(),
  /** Лайки (если сообщество их отдаёт): основа для сортировки «Популярные». */
  likes: z.object({ count: z.number().optional() }).loose().optional(),
  /** Характеристики товара (если у сообщества включены). */
  property_values: z
    .array(
      z.object({
        variant_id: z.number().optional(),
        variant_name: z.string().optional(),
        property_name: z.string().optional(),
        value_name: z.string().optional(),
        variant_value: z.string().optional(),
      }),
    )
    .optional(),
  /**
   * Варианты товара. Формат НЕ подтверждён живыми данными сообщества — парсится терпимо,
   * см. mapper.ts. Если поля нет, выбор вариантов в интерфейсе не показывается.
   */
  variants: z
    .array(z.object({ title: z.string().optional(), property_name: z.string().optional(), value: z.string().optional() }).loose())
    .optional(),
});
export type VkMarketItem = z.infer<typeof vkMarketItem>;

export const vkMarketList = z.object({
  count: z.number(),
  items: z.array(z.unknown()),
});

export const vkAlbum = z.object({
  id: z.number(),
  owner_id: z.number().optional(),
  title: z.string(),
  count: z.number().optional().default(0),
  photo: z.object({ sizes: z.array(photoSize).optional().default([]) }).optional(),
});
export type VkAlbum = z.infer<typeof vkAlbum>;

/** Профиль сообщества нам нужен только ради id и проверки, что раздел «Товары» включён. */
export const vkGroup = z.object({
  id: z.number(),
  name: z.string().optional(),
  screen_name: z.string().optional(),
  market: z.object({ enabled: z.union([z.boolean(), z.number()]).optional() }).loose().optional(),
});
export type VkGroup = z.infer<typeof vkGroup>;
