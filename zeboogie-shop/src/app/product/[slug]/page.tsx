import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { Accordion, type AccItem } from "@/components/product/Accordion";
import { BuyBox } from "@/components/product/BuyBox";
import { ProductGallery } from "@/components/product/ProductGallery";
import { MaterialNote } from "@/components/product/MaterialNote";
import { ProductRail } from "@/components/product/ProductRail";
import { RecentlyViewed } from "@/components/product/RecentlyViewed";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { EmptyState } from "@/components/ui/EmptyState";
import { Price } from "@/components/ui/Price";
import { Reveal } from "@/components/ui/Reveal";
import { brand } from "@/content/brand";
import { cardBadges, relatedProducts, toCard } from "@/lib/catalog/query";
import { findProductBySlug } from "@/lib/catalog/service";
import { isDemo } from "@/lib/config/env";
import { formatMoney } from "@/lib/format";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const found = await findProductBySlug((await params).slug);
  if (!found) return { title: "Товар не найден", robots: { index: false } };
  const { product } = found;
  const description = product.description
    ? product.description.slice(0, 160)
    : `${product.title}${product.price ? ` — ${formatMoney(product.price)}` : ""}. Ручная работа из старого дерева.`;
  return {
    title: product.title,
    description,
    alternates: { canonical: `/product/${product.slug}` },
    robots: product.status === "removed" ? { index: false } : undefined,
    openGraph: { title: product.title, description, images: product.images[0] ? [{ url: product.images[0].url }] : undefined },
  };
}

const BADGE_LABEL = { new: "Новинка", last: "Последний экземпляр", preorder: "Под заказ" } as const;

export default async function ProductPage({ params }: Props) {
  const { slug } = await params;
  const found = await findProductBySlug(slug);
  if (!found) notFound();
  const { catalog, product } = found;
  if (slug !== product.slug) permanentRedirect(`/product/${product.slug}`);

  if (product.status === "removed") {
    return (
      <section className="container-x py-24">
        <EmptyState title="Эта работа больше недоступна" action={<Link href="/catalog" className="btn btn-solid">Смотреть каталог</Link>}>
          Изделие снято с витрины. Возможно, оно уже нашло свой дом.
        </EmptyState>
      </section>
    );
  }

  const card = toCard(product);
  const related = relatedProducts(catalog.products, product, 6).map(toCard);
  const cat = product.categories[0];
  const badges = cardBadges(product);

  // Структурированные данные — только для реальных товаров и только подтверждённые поля.
  const jsonLd =
    !isDemo() && product.price
      ? {
          "@context": "https://schema.org",
          "@type": "Product",
          name: product.title,
          ...(product.description ? { description: product.description } : {}),
          ...(product.images.length ? { image: product.images.map((i) => i.url) } : {}),
          offers: {
            "@type": "Offer",
            price: (product.price.amount / 100).toFixed(2),
            priceCurrency: product.price.currency,
            ...(product.availability !== "unknown"
              ? { availability: product.availability === "in_stock" ? "https://schema.org/InStock" : "https://schema.org/OutOfStock" }
              : {}),
          },
        }
      : null;

  // Размеры показываем только если они есть в данных источника — ничего не выдумываем.
  const isDimension = (name: string) => /размер|габарит|высот|ширин|длин|глубин|диаметр|толщин/i.test(name);
  const dimensions = product.attributes.filter((a) => isDimension(a.name));
  const characteristics = product.attributes.filter((a) => !isDimension(a.name));
  const rows = [...dimensions, ...characteristics];

  const accordion: AccItem[] = [
    ...(product.description
      ? [{ id: "desc", title: "Описание", content: <p className="whitespace-pre-line">{product.description}</p> }]
      : []),
    {
      id: "size",
      title: "Размеры и материал",
      content: (
        <>
          {rows.length > 0 && (
            <dl className="mb-4 divide-y divide-line">
              {rows.map((a) => (
                <div key={a.name} className="flex justify-between gap-6 py-2.5 text-sm">
                  <dt className="text-ink-soft">{a.name}</dt>
                  <dd className="text-right text-ink">{a.value}</dd>
                </div>
              ))}
            </dl>
          )}
          <p>{brand.material.lead}</p>
          <p className="mt-2">{brand.material.note}</p>
        </>
      ),
    },
    {
      id: "delivery",
      title: "Доставка и оплата",
      content: (
        <>
          <p>{brand.delivery.blocks[1].text}</p>
          <p className="mt-2">{brand.delivery.blocks[2].text}</p>
          <Link href="/delivery" className="u-link mt-3 inline-flex min-h-11 items-center text-ink">Подробнее о заказе</Link>
        </>
      ),
    },
    { id: "care", title: "Уход за изделием", content: <p>{brand.care}</p> },
  ];

  return (
    <>
      <div className="container-x pb-6 pt-2 md:pt-4">
        {jsonLd && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }} />}
        <div className="pdp" data-title={product.title.length > 22 ? "long" : undefined}>
          <div className="pdp__crumbs">
            <Breadcrumbs
              items={[
                { label: "Главная", href: "/" },
                { label: "Каталог", href: "/catalog" },
                ...(cat ? [{ label: cat.title, href: `/catalog?category=${cat.id}` }] : []),
                { label: product.title },
              ]}
            />
          </div>

          <Reveal first soft className="pdp__gallery">
            <ProductGallery images={product.images} title={product.title} focal={product.focalPoint} />
          </Reveal>

          <div className="pdp__info">
            <Reveal first delay={80}>
              {(cat || badges.length > 0) && (
                <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  {cat && <span className="eyebrow max-md:hidden">{cat.title}</span>}
                  {badges.map((b) => (
                    <span key={b} className="tag" data-kind={b}>{BADGE_LABEL[b]}</span>
                  ))}
                </p>
              )}
              <h1 className="mt-2 text-[clamp(1.75rem,1.2rem+1.6vw,2.75rem)] font-light leading-[1.08]">{product.title}</h1>
              <div className="mt-3 flex flex-wrap items-baseline gap-x-5 gap-y-1">
                <Price price={product.price} oldPrice={product.oldPrice} size="lg" />
                {product.availability !== "unknown" && (
                  <p className="flex items-center gap-2 text-sm">
                    <span aria-hidden className={`size-2 rounded-full ${product.availability === "in_stock" ? "bg-moss" : "bg-danger"}`} />
                    {product.availability === "in_stock" ? "В наличии" : "Нет в наличии"}
                  </p>
                )}
              </div>
            </Reveal>

            <Reveal first delay={160} className="mt-5">
              <BuyBox card={card} options={product.options} vkUrl={product.vkUrl} />
            </Reveal>

            <Reveal first delay={240} className="mt-6">
              <Accordion items={accordion} />
            </Reveal>
          </div>
        </div>
      </div>

      <MaterialNote />

      {related.length > 0 && (
        <section className="container-x mt-20 md:mt-28" aria-labelledby="related">
          <Reveal>
            <p className="eyebrow">Продолжить знакомство</p>
            <h2 id="related" className="mb-8 mt-3 text-h2 font-light">Похожие работы</h2>
          </Reveal>
          <ProductRail items={related} label="Похожие работы" />
        </section>
      )}

      <RecentlyViewed current={card} />
    </>
  );
}
