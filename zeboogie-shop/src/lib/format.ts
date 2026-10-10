import type { Money } from "./types";

const SYMBOLS: Record<string, string> = { RUB: "₽", RUR: "₽", USD: "$", EUR: "€", KZT: "₸", BYN: "Br", UAH: "₴" };

/** Форматирует сумму в минимальных единицах. Без копеек, если они нулевые. */
export function formatMoney(money: Money): string {
  const major = money.amount / 100;
  const whole = Number.isInteger(major);
  const number = new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(major);
  const symbol = SYMBOLS[money.currency.toUpperCase()] ?? money.currency;
  return `${number} ${symbol}`;
}

export function discountPercent(price: Money, old: Money): number {
  return Math.round((1 - price.amount / old.amount) * 100);
}

/** Склонение: plural(5, ["товар","товара","товаров"]) */
export function plural(n: number, forms: [string, string, string]): string {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return forms[0];
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return forms[1];
  return forms[2];
}

const TRANSLIT: Record<string, string> = {
  а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e", ж: "zh", з: "z", и: "i", й: "y", к: "k",
  л: "l", м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "h", ц: "ts",
  ч: "ch", ш: "sh", щ: "sch", ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya",
};

/** Человекочитаемый slug: транслитерация + id товара (id делает URL стабильным при переименовании). */
export function makeSlug(title: string, itemId: number): string {
  const base = title
    .toLowerCase()
    .split("")
    .map((ch) => TRANSLIT[ch] ?? ch)
    .join("")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/g, "");
  return base ? `${base}-${itemId}` : `item-${itemId}`;
}

/** Достаёт id товара из конца slug. */
export function itemIdFromSlug(slug: string): number | null {
  const m = /-(\d+)$/.exec(slug);
  return m ? Number(m[1]) : null;
}

export function normalizeText(s: string): string {
  return s.toLowerCase().replace(/ё/g, "е").replace(/\s+/g, " ").trim();
}
