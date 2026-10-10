import { brand } from "@/content/brand";

const steps = [
  { t: "Выберите работы", d: "Добавьте понравившиеся изделия в корзину." },
  { t: "Отправьте заказ", d: "Мы подготовим текст заказа — его нужно отправить сообщением мастерам во ВКонтакте." },
  { t: "Обсудите детали", d: "Оплата и доставка согласуются в личных сообщениях." },
];

export function HowToOrder() {
  return (
    <section className="container-x pb-4 pt-8">
      <div className="grid gap-10 border-t border-line pt-12 lg:grid-cols-12">
        <h2 className="text-4xl md:text-5xl lg:col-span-4">Как заказать</h2>
        <ol className="grid gap-8 sm:grid-cols-3 lg:col-span-8">
          {steps.map((s, i) => (
            <li key={s.t}>
              <span className="font-serif text-5xl text-wood/80">{i + 1}</span>
              <h3 className="mt-3 font-sans text-base font-medium tracking-normal">{s.t}</h3>
              <p className="mt-1 text-sm leading-relaxed text-ink-soft">{s.d}</p>
            </li>
          ))}
        </ol>
      </div>
      <p className="mt-12 font-serif text-2xl italic text-ink-soft">{brand.greeting}</p>
    </section>
  );
}
