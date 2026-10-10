import type { Metadata } from "next";
import Link from "next/link";
import { brand } from "@/content/brand";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";

export const metadata: Metadata = { title: "О мастерской", description: brand.lead };

export default function AboutPage() {
  return (
    <div className="container-x py-8 md:py-12">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "О мастерской" }]} />
      <div className="mt-8 grid gap-12 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <p className="eyebrow">{brand.name} · {brand.descriptor}</p>
          <h1 className="mt-4 text-5xl leading-[1.02] md:text-7xl">Мы даём доскам вторую жизнь</h1>
          <p className="mt-8 text-xl leading-relaxed text-ink-soft">{brand.lead}</p>
        </div>
      </div>
      <div className="mt-16 grid gap-12 lg:grid-cols-12">
        <div className="space-y-6 text-lg leading-relaxed lg:col-span-6 lg:col-start-1">
          {brand.story.map((p) => <p key={p.slice(0, 20)}>{p}</p>)}
        </div>
        <aside className="lg:col-span-5 lg:col-start-8">
          <blockquote className="border-l-2 border-wood pl-6 font-serif text-3xl italic leading-snug">«{brand.pullQuote}»</blockquote>
          <p className="mt-10 leading-relaxed text-ink-soft">{brand.manifesto}</p>
          <p className="mt-6 leading-relaxed text-ink-soft">{brand.worldwide}</p>
          <p className="mt-8 font-serif text-2xl italic">{brand.greeting}</p>
          <Link href="/catalog" className="btn btn-solid mt-8">Смотреть работы</Link>
        </aside>
      </div>
    </div>
  );
}
