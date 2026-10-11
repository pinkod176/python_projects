import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { brand } from "@/content/brand";
import type { ProductCard } from "@/lib/types";
import { Reveal } from "@/components/ui/Reveal";
import { HeroSlider } from "./HeroSlider";

/**
 * Первый экран: слева название и кнопка «Каталог», ниже — витрина лучших работ (3–5 штук).
 * Какие работы показывать, решает мастерская: в данных витрины (src/content/curation.*.json) у них стоит featured и featuredOrder.
 */
export function Hero({ slides }: { slides: ProductCard[] }) {
  return (
    <section className="hero" aria-label="Zeboogie — рамки и предметы из старого дерева">
      <div className="hero__intro container-x">
        <div>
          <Reveal first>
            <p className="eyebrow">Мастерская · с {brand.since} года</p>
          </Reveal>
          <Reveal first delay={80}>
            <h1 className="hero__title">
              Вторая жизнь <em className="font-light italic text-copper">старых досок</em>
            </h1>
          </Reveal>
        </div>
        <Reveal first delay={180} className="hero__side">
          <p className="hero__lead">{brand.lead}</p>
          <div className="hero__actions">
            <Link href="/catalog" className="btn btn-solid">
              Каталог <ArrowRight aria-hidden className="size-4" />
            </Link>
            <Link href="/about" className="u-link inline-flex min-h-11 items-center text-[0.95rem]">О мастерской</Link>
          </div>
        </Reveal>
      </div>
      <HeroSlider slides={slides} />
    </section>
  );
}
