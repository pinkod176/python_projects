import { SectionHead } from "@/components/home/SectionHead";
import { Collections } from "@/components/home/Collections";
import { Hero } from "@/components/home/Hero";
import { HowToOrder } from "@/components/home/HowToOrder";
import { Story } from "@/components/home/Story";
import { Values } from "@/components/home/Values";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProductGrid } from "@/components/product/ProductGrid";
import { queryProducts } from "@/lib/catalog/query";
import { getCatalogState } from "@/lib/catalog/service";

export default async function HomePage() {
  const state = await getCatalogState();
  if (state.status === "error") {
    return (
      <section className="container-x py-24">
        <EmptyState title="Каталог временно недоступен">
          Не удалось загрузить товары. Обновите страницу чуть позже.
        </EmptyState>
      </section>
    );
  }
  const { products, collections } = state.catalog;
  const base = { sort: "new" as const, attrs: [], page: 1, pageSize: 8 };
  const newest = queryProducts(products, base);
  const cheapest = queryProducts(products, { ...base, sort: "price-asc", pageSize: 4 });
  const heroPicks = newest.items.filter((p) => p.image).slice(0, 3);

  return (
    <>
      <Hero picks={heroPicks} />
      <Collections collections={collections} />
      <section className="container-x py-8 md:py-12">
        <SectionHead eyebrow="Новое в мастерской" title="Новинки" href="/catalog?sort=new">
          Свежие работы из сообщества — в том порядке, в котором они появились.
        </SectionHead>
        {newest.items.length ? <ProductGrid items={newest.items} priorityCount={4} /> : <EmptyState title="Пока нет товаров" />}
      </section>
      <Story />
      {cheapest.items.length >= 4 && (
        <section className="container-x py-16 md:py-24">
          <SectionHead eyebrow="Подборка" title="Начать с малого" href="/catalog?sort=price-asc" linkLabel="По возрастанию цены">
            Самые доступные работы мастерской.
          </SectionHead>
          <ProductGrid items={cheapest.items} />
        </section>
      )}
      <Values />
      <HowToOrder />
    </>
  );
}
