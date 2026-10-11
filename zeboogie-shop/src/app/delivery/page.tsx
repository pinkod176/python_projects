import type { Metadata } from "next";
import Link from "next/link";
import { brand } from "@/content/brand";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Reveal } from "@/components/ui/Reveal";

export const metadata: Metadata = {
  title: brand.delivery.title,
  description: "Как оформить заказ, договориться о доставке и оплате.",
};

export default function DeliveryPage() {
  const d = brand.delivery;
  return (
    <div className="container-x pb-6 pt-6 md:pt-8">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: d.title }]} />
      <header className="mt-6 md:mt-8">
        <Reveal first>
          <p className="eyebrow">Заказ без сюрпризов</p>
          <h1 className="mt-3 text-h1 font-light">{d.title}</h1>
        </Reveal>
        <Reveal first delay={100}>
          <p className="mt-6 max-w-2xl text-lead text-ink-soft">{d.lead}</p>
        </Reveal>
      </header>

      <ol className="mt-12 grid gap-px overflow-hidden rounded-lg border border-line bg-line md:mt-16 md:grid-cols-2">
        {d.blocks.map((b, i) => (
          <Reveal key={b.title} as="li" delay={(i % 2) * 90} className="bg-paper p-6 md:p-10">
            <span aria-hidden className="font-display text-5xl font-light leading-none text-copper">{i + 1}</span>
            <h2 className="mt-5 text-h3 font-normal">{b.title}</h2>
            <p className="mt-3 max-w-md leading-relaxed text-ink-soft">{b.text}</p>
          </Reveal>
        ))}
      </ol>

      <Reveal className="mt-12 flex flex-wrap items-center justify-between gap-6 rounded-lg border border-line bg-paper-2 p-6 md:mt-16 md:p-10">
        <p className="max-w-md font-display text-h3 font-light italic">Остались вопросы? Напишите мастерам — ответят лично.</p>
        <div className="flex flex-wrap gap-3">
          <Link href="/contacts" className="btn btn-solid">Контакты</Link>
          <Link href="/catalog" className="btn btn-ghost">В каталог</Link>
        </div>
      </Reveal>
    </div>
  );
}
