import { Advantages } from "@/components/home/Advantages";
import { CategoryTiles } from "@/components/home/CategoryTiles";
import { Hero } from "@/components/home/Hero";
import { Interior, type InteriorShot } from "@/components/home/Interior";
import { SectionHead } from "@/components/home/SectionHead";
import { Story } from "@/components/home/Story";
import { Subscribe } from "@/components/home/Subscribe";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProductGrid } from "@/components/product/ProductGrid";
import { featuredProducts, queryProducts, toCard } from "@/lib/catalog/query";
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
  const { products, collections, shop } = state.catalog;
  const newest = queryProducts(products, { sort: "new", attrs: [], page: 1, pageSize: 8 });

  // Hero: работы, которые мастерская отметила (featured, по featuredOrder). Если отметок нет — самые новые с фото.
  const picked = featuredProducts(products, 5).map(toCard);
  const filler = newest.items.filter((c) => c.image && !picked.some((p) => p.vkId === c.vkId));
  const slides = [...picked, ...filler].slice(0, picked.length >= 3 ? picked.length : 5);

  const interior: InteriorShot[] = products
    .filter((p) => p.status === "active")
    .flatMap((p) => (p.interior ?? []).map((i) => ({ url: i.url, note: i.note, slug: p.slug, title: p.title })));

  const storyPhoto = newest.items.filter((p) => p.image)[5] ?? newest.items.find((p) => p.image);

  return (
    <>
      <Hero slides={slides} />
      <CategoryTiles collections={collections} />
      <section className="container-x pb-6 pt-2 md:pt-6" aria-labelledby="new-h">
        <SectionHead eyebrow="Новое в мастерской" title="Новые работы" titleId="new-h" href="/catalog?sort=new" linkLabel="Смотреть все">
          Свежие работы из сообщества — в том порядке, в котором они появились.
        </SectionHead>
        {newest.items.length ? <ProductGrid items={newest.items} trimOnPhone={4} numbered={false} /> : <EmptyState title="Пока нет товаров" />}
      </section>
      <div className="section-y">
        <Story photo={storyPhoto} />
      </div>
      <Advantages />
      <Interior shots={interior} />
      <Subscribe href={shop?.url} />
    </>
  );
}
