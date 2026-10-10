import type { Metadata } from "next";
import Link from "next/link";
import { brand } from "@/content/brand";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Reveal } from "@/components/ui/Reveal";

export const metadata: Metadata = { title: "О мастерской", description: brand.lead };

export default function AboutPage() {
  return (
    <div className="container-x pb-6 pt-8 md:pt-10">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "О мастерской" }]} />
      <header className="mt-8 grid gap-8 md:mt-12 lg:grid-cols-12">
        <div className="lg:col-span-9">
          <Reveal first>
            <p className="eyebrow">{brand.name} · {brand.descriptor}</p>
          </Reveal>
          <Reveal first delay={80}>
            <h1 className="mt-4 text-h1 font-light">Мы даём доскам <em className="font-light italic text-copper">вторую жизнь</em></h1>
          </Reveal>
          <Reveal first delay={160}>
            <p className="mt-8 max-w-2xl text-lead text-ink-soft">{brand.lead}</p>
          </Reveal>
        </div>
      </header>

      <div className="mt-16 grid gap-16 md:mt-24 lg:grid-cols-12">
        <div className="space-y-6 text-lg leading-relaxed lg:col-span-6">
          {brand.story.map((p, i) => (
            <Reveal key={p.slice(0, 20)} as="p" delay={i * 60}>{p}</Reveal>
          ))}
        </div>
        <aside className="lg:col-span-5 lg:col-start-8">
          <div className="lg:sticky lg:top-[calc(var(--header-h)+var(--space-3))]">
            <Reveal>
              <blockquote className="border-l-2 border-copper pl-6 font-display text-h3 font-light italic">«{brand.pullQuote}»</blockquote>
              <p className="mt-10 leading-relaxed text-ink-soft">{brand.manifesto}</p>
              <p className="mt-6 leading-relaxed text-ink-soft">{brand.worldwide}</p>
              <p className="mt-10 font-display text-h3 font-light italic">{brand.greeting}</p>
              <Link href="/catalog" className="btn btn-solid mt-8">Смотреть работы</Link>
            </Reveal>
          </div>
        </aside>
      </div>
    </div>
  );
}
