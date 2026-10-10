import Link from "next/link";
import { plural } from "@/lib/format";
import type { Collection } from "@/lib/types";
import { ProductImage } from "@/components/ui/ProductImage";
import { SectionHead } from "./SectionHead";

export function Collections({ collections }: { collections: Collection[] }) {
  if (!collections.length) return null;
  return (
    <section id="collections" className="container-x py-16 md:py-24">
      <SectionHead eyebrow="Подборки" title="Что делают мастера" />
      <ul className="grid grid-cols-2 gap-x-3 gap-y-10 md:grid-cols-4 md:gap-x-6">
        {collections.map((c, i) => (
          <li key={c.id} className={i % 2 === 1 ? "md:mt-14" : ""}>
            <Link href={`/catalog?category=${c.id}`} className="group block">
              <div className="mat">
                <div className="relative aspect-[4/5] overflow-hidden bg-paper-3">
                  <ProductImage src={c.image} alt="" sizes="(min-width:768px) 22vw, 50vw" className="transition-transform duration-700 motion-safe:group-hover:scale-105" />
                </div>
              </div>
              <div className="mt-3 flex items-baseline justify-between gap-3">
                <h3 className="font-serif text-xl md:text-2xl">{c.title}</h3>
                <span className="shrink-0 text-xs text-ink-soft">
                  {c.count} {plural(c.count, ["работа", "работы", "работ"])}
                </span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
