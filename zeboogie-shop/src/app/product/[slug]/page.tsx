import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { BuyBox } from "@/components/product/BuyBox";
import { ProductGallery } from "@/components/product/ProductGallery";
import { ProductGrid } from "@/components/product/ProductGrid";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { EmptyState } from "@/components/ui/EmptyState";
import { Price } from "@/components/ui/Price";
import { relatedProducts, toCard } from "@/lib/catalog/query";
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
  const related = relatedProducts(catalog.products, product, 4).map(toCard);
  const cat = product.categories[0];

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

  return (
    <div className="container-x py-8 md:py-12">
      {jsonLd && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }} />}
      <Breadcrumbs
        items={[
          { label: "Главная", href: "/" },
          { label: "Каталог", href: "/catalog" },
          ...(cat ? [{ label: cat.title, href: `/catalog?category=${cat.id}` }] : []),
          { label: product.title },
        ]}
      />

      <div className="mt-8 grid gap-10 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-6">
          <ProductGallery images={product.images} title={product.title} />
        </div>
        <div className="lg:col-span-6 lg:pt-4">
          {cat && <p className="eyebrow">{cat.title}</p>}
          <h1 className="mt-3 text-4xl leading-tight md:text-6xl">{product.title}</h1>
          <Price price={product.price} oldPrice={product.oldPrice} size="lg" className="mt-6" />
          {product.availability !== "unknown" && (
            <p className="mt-3 flex items-center gap-2 text-sm">
              <span aria-hidden className={`size-2 rounded-full ${product.availability === "in_stock" ? "bg-moss" : "bg-danger"}`} />
              {product.availability === "in_stock" ? "В наличии" : "Нет в наличии"}
            </p>
          )}

          <div className="rule mt-8 pt-8">
            <BuyBox card={card} options={product.options} vkUrl={product.vkUrl} />
          </div>

          {product.description && (
            <div className="rule mt-8 pt-8">
              <h2 className="eyebrow !font-sans">Описание</h2>
              <p className="mt-3 whitespace-pre-line leading-relaxed text-ink/90">{product.description}</p>
            </div>
          )}

          {product.attributes.length > 0 && (
            <div className="rule mt-8 pt-8">
              <h2 className="eyebrow !font-sans">Характеристики</h2>
              <dl className="mt-3 divide-y divide-line">
                {product.attributes.map((a) => (
                  <div key={a.name} className="flex justify-between gap-6 py-2.5 text-sm">
                    <dt className="text-ink-soft">{a.name}</dt>
                    <dd className="text-right">{a.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      </div>

      {related.length > 0 && (
        <section className="mt-24" aria-labelledby="related">
          <h2 id="related" className="mb-8 text-3xl md:text-4xl">Смотрите также</h2>
          <ProductGrid items={related} />
        </section>
      )}
    </div>
  );
}
