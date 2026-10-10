import { SORTS, type Sort } from "./query";

/** Состояние фильтров каталога в виде, удобном для URL и UI. Деньги — в основных единицах (рубли). */
export type UiParams = {
  q: string;
  category: string;
  sort: Sort;
  min: string;
  max: string;
  inStock: boolean;
  attrs: string[];
};

export const DEFAULT_PARAMS: UiParams = { q: "", category: "", sort: "new", min: "", max: "", inStock: false, attrs: [] };

export function paramsFromSearch(sp: URLSearchParams): UiParams {
  const sort = sp.get("sort");
  return {
    q: sp.get("q") ?? "",
    category: sp.get("category") ?? "",
    sort: (SORTS as readonly string[]).includes(sort ?? "") ? (sort as Sort) : "new",
    min: sp.get("min") ?? "",
    max: sp.get("max") ?? "",
    inStock: sp.get("inStock") === "1",
    attrs: sp.getAll("attr"),
  };
}

const toMinor = (v: string) => (v.trim() !== "" && Number.isFinite(Number(v)) && Number(v) >= 0 ? String(Math.round(Number(v) * 100)) : "");

/** Параметры для /api/catalog (цены переводятся в копейки). */
export function toApiQuery(p: UiParams, page: number, pageSize: number): string {
  const sp = new URLSearchParams();
  if (p.q.trim()) sp.set("q", p.q.trim());
  if (p.category) sp.set("category", p.category);
  if (p.sort !== "new") sp.set("sort", p.sort);
  if (toMinor(p.min)) sp.set("min", toMinor(p.min));
  if (toMinor(p.max)) sp.set("max", toMinor(p.max));
  if (p.inStock) sp.set("inStock", "1");
  p.attrs.forEach((a) => sp.append("attr", a));
  sp.set("page", String(page));
  sp.set("pageSize", String(pageSize));
  return sp.toString();
}

/** Адрес страницы (без page/pageSize). */
export function toPageQuery(p: UiParams): string {
  const sp = new URLSearchParams(toApiQuery(p, 1, 1));
  sp.delete("page");
  sp.delete("pageSize");
  if (p.min.trim()) sp.set("min", p.min.trim());
  else sp.delete("min");
  if (p.max.trim()) sp.set("max", p.max.trim());
  else sp.delete("max");
  return sp.toString();
}
