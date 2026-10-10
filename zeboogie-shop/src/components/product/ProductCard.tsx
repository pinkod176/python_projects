import Link from "next/link";
import type { ProductCard as Card } from "@/lib/types";
import { Price } from "@/components/ui/Price";
import { ProductImage } from "@/components/ui/ProductImage";
import { FavoriteButton } from "./FavoriteButton";
import { QuickAdd } from "./QuickAdd";

type Props = { card: Card; index?: number; priority?: boolean; sizes?: string };

export function ProductCard({ card, index, priority, sizes = "(min-width:1024px) 22vw, (min-width:640px) 33vw, 50vw" }: Props) {
  const unavailable = card.availability === "unavailable";
  return (
    <article className="group relative flex flex-col">
      <Link href={`/product/${card.slug}`} className="block" aria-label={card.title}>
        <div className="mat">
          <div className="relative aspect-[4/5] overflow-hidden bg-paper-3">
            <ProductImage
              src={card.image}
              alt={card.title}
              sizes={sizes}
              priority={priority}
              className={`transition-transform duration-700 ease-out-soft motion-safe:group-hover:scale-[1.04] ${unavailable ? "opacity-55 grayscale" : ""}`}
            />
            {unavailable && (
              <span className="absolute left-2 top-2 bg-ink px-2 py-1 text-xs text-paper">Нет в наличии</span>
            )}
          </div>
        </div>
        <div className="mt-3 flex items-start gap-3">
          {index !== undefined && (
            <span aria-hidden className="mt-1 hidden font-serif text-xs text-ink-soft sm:block">
              №{String(index + 1).padStart(2, "0")}
            </span>
          )}
          <div className="min-w-0 flex-1">
            <h3 className="font-sans text-[0.95rem] font-normal leading-snug tracking-normal [text-wrap:pretty] md:text-base">
              {card.title}
            </h3>
            {card.categoryTitle && <p className="mt-0.5 truncate text-xs text-ink-soft">{card.categoryTitle}</p>}
            <Price price={card.price} oldPrice={card.oldPrice} className="mt-1.5 text-[0.95rem]" />
          </div>
        </div>
      </Link>
      <FavoriteButton card={card} className="absolute right-3 top-3 sm:right-4 sm:top-4" />
      {!unavailable && <QuickAdd card={card} />}
    </article>
  );
}
