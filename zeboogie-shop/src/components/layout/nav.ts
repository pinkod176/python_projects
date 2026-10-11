import { brand } from "@/content/brand";
import type { Collection } from "@/lib/types";

export type NavTab = {
  key: string;
  href: string;
  label: string;
  /** У вкладки «Каталог» есть выпадающий список. */
  dropdown?: boolean;
  /** Вкладка-подборка: подсвечивается, когда в каталоге выбрана эта подборка. */
  categoryId?: string;
};

export type NavCategory = Pick<Collection, "id" | "title" | "count" | "image" | "imageFocal">;

/**
 * Вкладки шапки: «Каталог» (с выпадающим списком всех подборок), самые большие подборки (по числу работ),
 * затем страницы мастерской. Названия подборок берутся из данных, а не прописаны в коде.
 */
export function buildNav(collections: Collection[]): { tabs: NavTab[]; categories: NavCategory[] } {
  const categories: NavCategory[] = collections.map(({ id, title, count, image, imageFocal }) => ({ id, title, count, image, imageFocal }));
  const main = [...categories].sort((a, b) => b.count - a.count).slice(0, brand.nav.mainCategories);
  // Порядок вкладок-подборок — как в списке подборок сообщества, а не по размеру.
  const mainOrdered = categories.filter((c) => main.some((m) => m.id === c.id));
  const tabs: NavTab[] = [
    { key: "catalog", href: "/catalog", label: "Каталог", dropdown: true },
    ...mainOrdered.map((c) => ({ key: c.id, href: `/catalog?category=${c.id}`, label: c.title, categoryId: c.id })),
    ...brand.nav.info.map((i) => ({ key: i.href, href: i.href, label: i.label })),
  ];
  return { tabs, categories };
}

/** Какая вкладка сейчас активна (ровно одна или ни одной). */
export function activeTabKey(tabs: NavTab[], pathname: string, category: string | null): string | null {
  if (pathname === "/catalog" && category) {
    const byCategory = tabs.find((t) => t.categoryId === category);
    if (byCategory) return byCategory.key;
  }
  if (pathname.startsWith("/catalog") || pathname.startsWith("/product/")) return "catalog";
  return tabs.find((t) => !t.dropdown && !t.categoryId && t.href === pathname)?.key ?? null;
}
