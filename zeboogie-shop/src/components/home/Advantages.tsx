import { Hand, Package, Sparkles, TreeDeciduous } from "lucide-react";
import { brand } from "@/content/brand";
import { Reveal } from "@/components/ui/Reveal";

const icons = [TreeDeciduous, Hand, Sparkles, Package];

/** Четыре преимущества мастерской. Тексты — из brand.ts. */
export function Advantages() {
  return (
    <section className="container-x section-y" aria-label="Преимущества">
      <ul className="grid grid-cols-2 gap-3 md:gap-6 lg:grid-cols-4">
        {brand.advantages.map((v, i) => {
          const Icon = icons[i] ?? Sparkles;
          return (
            <Reveal key={v.title} as="li" delay={i * 80} className="min-w-0 rounded-lg border border-line bg-paper-2 p-5 md:p-8">
              <Icon aria-hidden className="size-7 text-copper" strokeWidth={1.25} />
              <h3 className="mt-5 text-[1.375rem] font-normal leading-[1.1] md:mt-8 md:text-[1.625rem]">{v.title}</h3>
              <p className="mt-2 text-[0.9375rem] leading-relaxed text-ink-soft">{v.text}</p>
            </Reveal>
          );
        })}
      </ul>
    </section>
  );
}
