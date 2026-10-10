import Link from "next/link";
import { plural } from "@/lib/format";
import type { Collection } from "@/lib/types";
import { ProductImage } from "@/components/ui/ProductImage";
import { Reveal } from "@/components/ui/Reveal";
import { SectionHead } from "./SectionHead";

export function Collections({ collections }: { collections: Collection[] }) {
  if (!collections.length) return null;
  return (
    <section id="collections" className="container-x section-y">
      <SectionHead eyebrow="Подборки" title="Что делают мастера" href="/catalog" linkLabel="Весь каталог" />
      <ul className="grid grid-cols-2 gap-x-4 gap-y-10 md:grid-cols-4 md:gap-x-6">
        {collections.map((c, i) => (
          <Reveal key={c.id} as="li" delay={(i % 4) * 70} className={i % 2 === 1 ? "md:mt-12" : ""}>
            <Link href={`/catalog?category=${c.id}`} className="card block">
              <div className="card__media mat">
                <div className="mat-photo">
                  <ProductImage src={c.image} alt="" sizes="(min-width:768px) 22vw, 46vw" className="card__img" />
                </div>
              </div>
              <div className="mt-4 flex flex-col gap-1 lg:flex-row lg:items-baseline lg:justify-between lg:gap-3">
                <h3 className="font-display text-xl leading-tight md:text-[1.65rem]">{c.title}</h3>
                <span className="text-xs text-ink-soft lg:shrink-0">
                  {c.count} {plural(c.count, ["работа", "работы", "работ"])}
                </span>
              </div>
            </Link>
          </Reveal>
        ))}
      </ul>
    </section>
  );
}
