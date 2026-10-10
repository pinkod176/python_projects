import { Hand, Layers, TreeDeciduous } from "lucide-react";
import { brand } from "@/content/brand";
import { Reveal } from "@/components/ui/Reveal";

const icons = [TreeDeciduous, Layers, Hand];

/** «Из чего сделано»: рассказ мастерской о материале. Тексты — из brand.ts, это общая информация о мастерской, а не характеристики конкретной вещи. */
export function MaterialNote() {
  const m = brand.material;
  return (
    <section aria-labelledby="material" className="mt-24 border-y border-line bg-paper-2 md:mt-32">
      <div className="container-x grid gap-12 py-16 md:py-24 xl:grid-cols-12">
        <Reveal className="xl:col-span-5">
          <p className="eyebrow">Материал</p>
          <h2 id="material" className="mt-3 text-h2 font-light">{m.title}</h2>
          <p className="mt-6 max-w-md text-ink-soft">{m.lead}</p>
        </Reveal>
        <ul className="grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-3 xl:col-span-7">
          {m.points.map((p, i) => {
            const Icon = icons[i] ?? Layers;
            return (
              <Reveal key={p.title} as="li" delay={i * 90} className="bg-paper p-6 md:p-8">
                <Icon aria-hidden className="size-7 text-copper" strokeWidth={1.25} />
                <h3 className="mt-6 font-sans text-base font-medium tracking-normal">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{p.text}</p>
              </Reveal>
            );
          })}
        </ul>
        <p className="text-sm text-ink-soft xl:col-span-7 xl:col-start-6">{m.note}</p>
      </div>
    </section>
  );
}
