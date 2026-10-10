import Link from "next/link";
import { ArrowDownRight, ArrowRight } from "lucide-react";
import { brand } from "@/content/brand";
import { formatMoney } from "@/lib/format";
import type { ProductCard } from "@/lib/types";
import { ProductImage } from "@/components/ui/ProductImage";

/** Первый экран: крупная типографика слева, «стена с рамками» справа. */
export function Hero({ picks }: { picks: ProductCard[] }) {
  const [a, b, c] = picks;
  const mat = (p: ProductCard | undefined, cls: string, sizes: string, priority = false) =>
    p && (
      <Link href={`/product/${p.slug}`} className={`group absolute block ${cls}`} aria-label={p.title}>
        <div className="mat">
          <div className="relative aspect-[4/5] overflow-hidden">
            <ProductImage src={p.image} alt={p.title} sizes={sizes} priority={priority} className="transition-transform duration-700 motion-safe:group-hover:scale-105" />
          </div>
        </div>
        <p className="mt-2 truncate text-xs text-ink-soft">
          {p.title}
          {p.price && <span className="text-ink"> · {formatMoney(p.price)}</span>}
        </p>
      </Link>
    );

  return (
    <section className="container-x grid gap-12 pb-16 pt-10 md:pt-16 lg:grid-cols-12 lg:gap-8 lg:pb-24 lg:pt-20">
      <div className="reveal flex flex-col justify-between lg:col-span-7">
        <div>
          <p className="eyebrow">Мастерская · с {brand.since} года</p>
          <h1 className="mt-5 text-[clamp(3rem,7.2vw,6.6rem)] font-light leading-[0.95] tracking-[-0.03em]">
            Вторая жизнь <em className="font-light italic text-wood">старых досок</em>
          </h1>
          <p className="mt-8 max-w-xl text-lg leading-relaxed text-ink-soft">{brand.lead}</p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/catalog" className="btn btn-solid">
              Смотреть работы <ArrowRight aria-hidden className="size-4" />
            </Link>
            <Link href="/about" className="btn btn-ghost">О мастерской</Link>
          </div>
        </div>
        <a href="#collections" className="mt-14 hidden w-fit items-center gap-2 text-sm text-ink-soft hover:text-ink lg:inline-flex">
          Подборки <ArrowDownRight aria-hidden className="size-4" />
        </a>
      </div>

      {/* стена */}
      <div className="reveal relative min-h-[30rem] sm:min-h-[40rem] lg:col-span-5 lg:min-h-[44rem]" style={{ animationDelay: "120ms" }}>
        {mat(a, "right-0 top-0 w-[58%]", "(min-width:1024px) 22vw, 50vw", true)}
        {mat(b, "left-0 top-[24%] w-[38%]", "(min-width:1024px) 14vw, 36vw")}
        {mat(c, "bottom-0 right-[10%] w-[36%]", "(min-width:1024px) 12vw, 30vw")}
      </div>
    </section>
  );
}
