import Link from "next/link";
import type { ProductCard as Card } from "@/lib/types";
import { Price } from "@/components/ui/Price";
import { CardMedia } from "./CardMedia";
import { FavoriteButton } from "./FavoriteButton";
import { CardActions } from "./QuickAdd";

type Props = { card: Card; index?: number; priority?: boolean; eager?: boolean; sizes?: string; headingLevel?: 2 | 3 };

const DEFAULT_SIZES = "(min-width:1200px) 22vw, (min-width:640px) 30vw, 46vw";

/**
 * Карточка товара. Два соседних блока: фото в паспарту (со своими кнопками) и ссылка с названием и ценой.
 * Кнопки лежат рядом со ссылкой, а не внутри неё: тап по сердечку или «+» не открывает страницу товара.
 */
export function ProductCard({ card, index, priority, eager, headingLevel = 3, sizes = DEFAULT_SIZES }: Props) {
  const unavailable = card.availability === "unavailable";
  const Heading = headingLevel === 2 ? "h2" : "h3";
  const href = `/product/${card.slug}`;
  return (
    <article className="card" data-unavailable={unavailable || undefined}>
      <div className="card__media mat">
        <CardMedia
          href={href}
          image={card.image}
          hoverImage={card.hoverImage}
          focal={card.focalPoint}
          badges={card.badges}
          unavailable={unavailable}
          sizes={sizes}
          priority={priority}
          eager={eager}
        />
        <FavoriteButton card={card} className="card__fav" />
        {!unavailable && <CardActions card={card} />}
      </div>
      <Link href={href} className="card__body">
        <div className="card__meta">
          {index !== undefined && (
            <span aria-hidden className="card__no">
              №{String(index + 1).padStart(2, "0")}
            </span>
          )}
        </div>
        <Heading className="card__title">{card.title}</Heading>
        {card.categoryTitle && <p className="card__cat">{card.categoryTitle}</p>}
        <Price price={card.price} oldPrice={card.oldPrice} className="card__price" />
      </Link>
    </article>
  );
}
