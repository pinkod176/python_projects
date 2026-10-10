import Link from "next/link";
import { brand } from "@/content/brand";
import { Reveal } from "@/components/ui/Reveal";

const steps = [
  { t: "Выберите работы", d: "Добавьте понравившиеся изделия в корзину." },
  { t: "Отправьте заказ", d: "Мы подготовим текст заказа — его нужно отправить сообщением мастерам во ВКонтакте." },
  { t: "Обсудите детали", d: "Оплата и доставка согласуются в личных сообщениях." },
];

export function HowToOrder() {
  return (
    <section className="container-x pb-6 pt-4">
      <div className="grid gap-12 border-t border-line pt-16 lg:grid-cols-12">
        <Reveal className="lg:col-span-4">
          <p className="eyebrow">Три шага</p>
          <h2 className="mt-3 text-h2 font-light">Как заказать</h2>
        </Reveal>
        <ol className="grid gap-10 sm:grid-cols-3 lg:col-span-8">
          {steps.map((s, i) => (
            <Reveal key={s.t} as="li" delay={i * 90}>
              <span className="font-display text-6xl font-light leading-none text-copper">{i + 1}</span>
              <h3 className="mt-5 font-sans text-base font-medium tracking-normal">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{s.d}</p>
            </Reveal>
          ))}
        </ol>
      </div>
      <Reveal className="mt-20 flex flex-wrap items-center justify-between gap-6 rounded-lg border border-line bg-paper-2 p-8 md:p-12">
        <p className="font-display text-h3 font-light italic">{brand.greeting}</p>
        <Link href="/catalog" className="btn btn-solid">Перейти в каталог</Link>
      </Reveal>
    </section>
  );
}
