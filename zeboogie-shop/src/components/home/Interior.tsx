import Link from "next/link";
import { ProductImage } from "@/components/ui/ProductImage";
import { Reveal } from "@/components/ui/Reveal";
import { SectionHead } from "./SectionHead";

export type InteriorShot = { url: string; note?: string; slug: string; title: string };

/**
 * «В интерьере»: настоящие снимки работ в обстановке (их отметила мастерская в данных витрины — поле interior).
 * Если таких снимков нет, блок на главной не показывается: примеры интерьеров и отзывы не выдумываем.
 */
export function Interior({ shots }: { shots: InteriorShot[] }) {
  if (shots.length < 2) return null;
  return (
    <section className="container-x pb-6" aria-labelledby="interior-h">
      <SectionHead eyebrow="Как это выглядит дома" title="В интерьере" titleId="interior-h" />
      <ul className="interior" data-count={Math.min(shots.length, 4)}>
        {shots.slice(0, 4).map((s, i) => (
          <Reveal key={s.url} as="li" delay={i * 80}>
            <Link href={`/product/${s.slug}`} className="interior__item card">
              <span className="card__media mat block">
                <span className="mat-photo interior__photo">
                  <ProductImage src={s.url} alt={s.note ? `${s.title}: ${s.note}` : s.title} sizes="(min-width:1024px) 22vw, 46vw" className="card__img" />
                </span>
              </span>
              <span className="mt-3 block text-sm text-ink-soft">{s.title}</span>
            </Link>
          </Reveal>
        ))}
      </ul>
    </section>
  );
}
