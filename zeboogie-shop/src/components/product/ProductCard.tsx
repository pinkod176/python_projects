import Link from "next/link";
import type { ProductCard as Card } from "@/lib/types";
import { Price } from "@/components/ui/Price";
import { ProductImage } from "@/components/ui/ProductImage";
import { FavoriteButton } from "./FavoriteButton";
import { QuickAdd } from "./QuickAdd";

type Props = { card: Card; index?: number; priority?: boolean; eager?: boolean; sizes?: string; headingLevel?: 2 | 3 };

export function ProductCard({ card, index, priority, eager, headingLevel = 3, sizes = "(min-width:1280px) 22vw, (min-width:768px) 30vw, (min-width:520px) 45vw, 92vw" }: Props) {
  const unavailable = card.availability === "unavailable";
  const Heading = headingLevel === 2 ? "h2" : "h3";
  return (
    <article className="card">
      <Link href={`/product/${card.slug}`} className="block">
        <div className="card__media mat">
          <div className="mat-photo">
            <ProductImage
              src={card.image}
              alt=""
              sizes={sizes}
              priority={priority}
              eager={eager}
              className={`card__img ${unavailable ? "opacity-55 grayscale" : ""}`}
            />
            {unavailable && (
              <span className="absolute left-2 top-2 rounded-sm bg-footer px-2 py-1 text-xs text-on-accent">Нет в наличии</span>
            )}
          </div>
        </div>
        <div className="mt-4 flex items-start gap-3">
          {index !== undefined && (
            <span aria-hidden className="mt-[0.2rem] text-xs tabular-nums text-ink-soft">
              №{String(index + 1).padStart(2, "0")}
            </span>
          )}
          <div className="min-w-0 flex-1">
            <Heading className="font-sans text-[1.0625rem] font-normal leading-snug tracking-normal [text-wrap:pretty]">{card.title}</Heading>
            {card.categoryTitle && <p className="mt-0.5 truncate text-sm text-ink-soft">{card.categoryTitle}</p>}
            <Price price={card.price} oldPrice={card.oldPrice} className="mt-2" />
          </div>
        </div>
      </Link>
      <FavoriteButton card={card} className="card__fav" />
      {!unavailable && <QuickAdd card={card} />}
    </article>
  );
}
