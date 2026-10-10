import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { brand } from "@/content/brand";

export function Story() {
  return (
    <section className="bg-moss text-paper">
      <div className="container-x grid gap-12 py-20 md:py-28 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <p className="text-xs uppercase tracking-[0.18em] text-paper/70">О мастерской</p>
          <blockquote className="mt-5 font-serif text-[clamp(2rem,5vw,4rem)] font-light leading-[1.08] tracking-[-0.02em]">
            «{brand.manifesto}»
          </blockquote>
        </div>
        <div className="lg:col-span-5 lg:pt-12">
          <p className="leading-relaxed text-paper/85">{brand.story[0]}</p>
          <dl className="mt-10 grid grid-cols-3 gap-4 border-t border-paper/25 pt-6">
            {brand.facts.map((f) => (
              <div key={f.value}>
                <dt className="font-serif text-2xl md:text-3xl">{f.value}</dt>
                <dd className="mt-2 text-xs leading-snug text-paper/75">{f.label}</dd>
              </div>
            ))}
          </dl>
          <Link href="/about" className="mt-10 inline-flex min-h-11 items-center gap-2 border-b border-paper hover:text-paper/80">
            Читать историю <ArrowRight aria-hidden className="size-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
