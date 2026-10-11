import type { Metadata } from "next";
import { CatalogBrowser } from "@/components/catalog/CatalogBrowser";
import { EmptyState } from "@/components/ui/EmptyState";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { paramsFromSearch, toApiQuery } from "@/lib/catalog/params";
import { queryProducts } from "@/lib/catalog/query";
import { getCatalogState } from "@/lib/catalog/service";

export const metadata: Metadata = {
  title: "Каталог",
  description: "Рамки, украшения и арт-объекты из старого дерева ручной работы.",
};

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function CatalogPage({ searchParams }: Props) {
  const raw = await searchParams;
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(raw)) (Array.isArray(v) ? v : v === undefined ? [] : [v]).forEach((x) => sp.append(k, x));
  const params = paramsFromSearch(sp);

  const state = await getCatalogState();
  if (state.status === "error") {
    return (
      <section className="container-x py-24">
        <EmptyState title="Каталог временно недоступен">Не удалось загрузить товары. Попробуйте обновить страницу чуть позже.</EmptyState>
      </section>
    );
  }
  const api = new URLSearchParams(toApiQuery(params, 1, 12));
  const initial = queryProducts(state.catalog.products, {
    q: params.q || undefined,
    category: params.category || undefined,
    sort: params.sort,
    min: api.get("min") ? Number(api.get("min")) : undefined,
    max: api.get("max") ? Number(api.get("max")) : undefined,
    inStock: params.inStock,
    attrs: params.attrs,
    page: 1,
    pageSize: 12,
  });
  const current = state.catalog.collections.find((c) => c.id === params.category);

  return (
    <div className="container-x pb-6 pt-2 md:pt-4">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "Каталог", href: current ? "/catalog" : undefined }, ...(current ? [{ label: current.title }] : [])]} />
      {/* key: при переходе по ссылке с другими параметрами (например, подборка из шапки) браузер каталога пересоздаётся. Клиентская фильтрация меняет URL через replaceState и сервер не перерисовывает, поэтому ключ тогда не меняется. */}
      <CatalogBrowser key={sp.toString()} initial={initial} initialParams={params} />
    </div>
  );
}
