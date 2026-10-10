import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { brand } from "@/content/brand";
import type { ProductCard } from "@/lib/types";
import { ProductImage } from "@/components/ui/ProductImage";
import { Reveal } from "@/components/ui/Reveal";

/** «О мастерской»: история материала — старое дерево и ручная работа. Тексты — из brand.ts (рассказ владельца). */
export function Story({ photo }: { photo?: ProductCard }) {
  return (
    <section className="bg-moss text-on-accent">
      <div className="container-x grid items-center gap-12 py-16 md:py-24 lg:grid-cols-12 lg:gap-16">
        {photo && (
          <Reveal className="lg:col-span-5">
            <Link href={`/product/${photo.slug}`} className="mat card mx-auto block max-w-sm lg:max-w-none" aria-label={photo.title}>
              <span className="mat-photo">
                <ProductImage src={photo.image} alt={photo.title} sizes="(min-width:1024px) 30vw, 90vw" className="card__img" />
              </span>
            </Link>
          </Reveal>
        )}
        <div className={photo ? "lg:col-span-7" : "lg:col-span-10"}>
          <Reveal>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-on-accent-soft">О мастерской</p>
            <blockquote className="mt-5 font-display text-h2 font-light italic">«{brand.manifesto}»</blockquote>
          </Reveal>
          <Reveal delay={120}>
            <p className="mt-8 max-w-xl leading-relaxed text-on-accent-soft">{brand.story[0]}</p>
            <p className="mt-4 max-w-xl leading-relaxed text-on-accent-soft">{brand.story[1]}</p>
          </Reveal>
          <Reveal as="dl" delay={200} className="mt-10 grid max-w-xl grid-cols-3 gap-4 border-t border-on-accent/25 pt-6">
            {brand.facts.map((f) => (
              <div key={f.value}>
                <dt className="font-display text-3xl font-light md:text-4xl">{f.value}</dt>
                <dd className="mt-2 text-xs leading-snug text-on-accent-soft">{f.label}</dd>
              </div>
            ))}
          </Reveal>
          <Reveal delay={260}>
            <Link href="/about" className="u-link mt-10 inline-flex min-h-11 items-center gap-2">
              Читать историю <ArrowRight aria-hidden className="size-4" />
            </Link>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
