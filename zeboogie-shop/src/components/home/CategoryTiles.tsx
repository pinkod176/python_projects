import Link from "next/link";
import { plural } from "@/lib/format";
import type { Collection } from "@/lib/types";
import { ProductImage } from "@/components/ui/ProductImage";
import { Reveal } from "@/components/ui/Reveal";
import { SectionHead } from "./SectionHead";

/** Крупные плитки подборок: фото в паспарту, название и число работ на мягком градиенте. Подборки и фото берутся из данных. */
export function CategoryTiles({ collections }: { collections: Collection[] }) {
  const tiles = [...collections].sort((a, b) => b.count - a.count).slice(0, 4);
  if (!tiles.length) return null;
  return (
    <section id="collections" className="container-x section-y" aria-labelledby="collections-h">
      <SectionHead eyebrow="Подборки" title="Что делают мастера" titleId="collections-h" href="/catalog" linkLabel="Весь каталог" />
      <ul className="tiles" data-count={tiles.length}>
        {tiles.map((c, i) => (
          <Reveal key={c.id} as="li" delay={(i % 4) * 70}>
            <Link href={`/catalog?category=${c.id}`} className="tile card">
              <span className="card__media mat block">
                <span className="mat-photo tile__photo">
                  <ProductImage src={c.image} alt="" focal={c.imageFocal} sizes="(min-width:1024px) 22vw, 46vw" className="card__img" />
                  <span className="tile__shade" aria-hidden />
                  <span className="tile__text">
                    <span className="tile__title">{c.title}</span>
                    <span className="tile__count">{c.count} {plural(c.count, ["работа", "работы", "работ"])}</span>
                  </span>
                </span>
              </span>
            </Link>
          </Reveal>
        ))}
      </ul>
    </section>
  );
}
