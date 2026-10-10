import { Hand, Layers, TreeDeciduous } from "lucide-react";
import { brand } from "@/content/brand";
import { Reveal } from "@/components/ui/Reveal";

const icons = [TreeDeciduous, Hand, Layers];

export function Values() {
  return (
    <section className="container-x section-y" aria-label="Преимущества">
      <ul className="grid gap-4 md:grid-cols-3 md:gap-6">
        {brand.values.map((v, i) => {
          const Icon = icons[i] ?? Layers;
          return (
            <Reveal key={v.title} as="li" delay={i * 90} className="min-w-0 rounded-lg border border-line bg-paper-2 p-8 md:p-6 lg:p-10">
              <Icon aria-hidden className="size-8 text-copper" strokeWidth={1.25} />
              <h3 className="mt-8 text-[1.75rem] font-normal leading-[1.1] md:text-2xl lg:text-h3">{v.title}</h3>
              <p className="mt-3 text-ink-soft">{v.text}</p>
            </Reveal>
          );
        })}
      </ul>
    </section>
  );
}
