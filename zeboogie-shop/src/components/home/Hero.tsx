import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { brand } from "@/content/brand";
import { formatMoney } from "@/lib/format";
import type { ProductCard } from "@/lib/types";
import { Reveal } from "@/components/ui/Reveal";
import { ProductImage } from "@/components/ui/ProductImage";

/**
 * Первый экран на всю высоту окна: слева короткий заголовок и мягкая кнопка, справа крупное фото изделия
 * в паспарту и второе, поменьше, «висящее» рядом. Фото берутся из каталога (самые новые работы).
 */
export function Hero({ picks }: { picks: ProductCard[] }) {
  const [main, second] = picks;
  return (
    <section className="container-x grid min-h-[calc(100svh-var(--header-h))] items-center gap-10 py-10 lg:grid-cols-12 lg:gap-8 lg:py-12">
      {/* На телефоне обёртка «растворяется» (contents): заголовок → фото → описание и кнопки. На десктопе — одна колонка слева. */}
      <div className="contents lg:col-span-6 lg:block">
        <div className="order-1">
          <Reveal first>
            <p className="eyebrow">Мастерская · с {brand.since} года</p>
          </Reveal>
          <Reveal first delay={80}>
            <h1 className="mt-6 text-display font-light">
              Вторая жизнь <em className="font-light italic text-copper">старых досок</em>
            </h1>
          </Reveal>
        </div>
        <div className="order-3 lg:mt-8">
          <Reveal first delay={180}>
            <p className="max-w-lg text-lead text-ink-soft">{brand.lead}</p>
          </Reveal>
          <Reveal first delay={280} className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-5">
            <Link href="/catalog" className="btn btn-solid">
              Смотреть работы <ArrowRight aria-hidden className="size-4" />
            </Link>
            <Link href="/about" className="u-link py-2 text-[0.95rem]">О мастерской</Link>
          </Reveal>
          <Reveal first delay={380}>
            <ul className="mt-12 flex flex-wrap gap-x-8 gap-y-2 border-t border-line pt-6 text-sm text-ink-soft lg:mt-14">
              {brand.tags.map((t) => (
                <li key={t} className="flex items-center gap-2.5">
                  <span aria-hidden className="size-1.5 rounded-full bg-copper" />
                  {t}
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </div>

      {main && (
        <Reveal first soft delay={160} className="relative order-2 mx-auto w-full max-w-[26rem] lg:order-none lg:col-span-6 lg:mr-0 lg:max-w-[34rem] lg:justify-self-end">
          <Link href={`/product/${main.slug}`} className="group block">
            <div className="mat shadow-soft">
              <div className="mat-photo">
                <ProductImage src={main.image} alt="" sizes="(min-width:1024px) 34rem, 92vw" priority className="hero-img" />
              </div>
            </div>
            <p className="mt-4 flex items-baseline justify-between gap-4 text-sm">
              <span><span className="text-ink-soft">№01</span> <span className="ml-2">{main.title}</span></span>
              {main.price && <span className="font-medium tabular-nums">{formatMoney(main.price)}</span>}
            </p>
          </Link>
          {second && (
            <Link
              href={`/product/${second.slug}`}
              aria-label={`${second.title}${second.price ? `, ${formatMoney(second.price)}` : ""}`}
              className="mat shadow-soft absolute -left-3 bottom-12 hidden w-[38%] sm:block lg:-left-24 lg:bottom-16"
            >
              <span className="mat-photo">
                <ProductImage src={second.image} alt="" sizes="(min-width:1024px) 13rem, 40vw" />
              </span>
            </Link>
          )}
        </Reveal>
      )}
    </section>
  );
}
