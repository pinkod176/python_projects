"use client";

import Link from "next/link";
import { useState } from "react";
import type { ProductBadge } from "@/lib/types";
import { ProductImage } from "@/components/ui/ProductImage";

const BADGE_LABEL: Record<ProductBadge, string> = { new: "Новинка", last: "Последний экземпляр", preorder: "Под заказ" };

type Props = {
  href: string;
  image: string | null;
  hoverImage?: string;
  focal?: string;
  badges?: ProductBadge[];
  unavailable?: boolean;
  sizes: string;
  priority?: boolean;
  eager?: boolean;
};

/**
 * Фото карточки. Второе фото (при наведении) подгружается только когда мышь впервые зашла на карточку —
 * ни на телефонах, ни при простой прокрутке каталога лишние файлы не качаются.
 * Ссылка-фото дублирует ссылку на название, поэтому скрыта от скринридеров и не берёт фокус с клавиатуры.
 */
export function CardMedia({ href, image, hoverImage, focal, badges = [], unavailable, sizes, priority, eager }: Props) {
  const [warm, setWarm] = useState(false);
  const tags = [...(unavailable ? (["soldout"] as const) : []), ...badges.filter((b) => !unavailable || b !== "new")].slice(0, 2);
  return (
    <Link
      href={href}
      tabIndex={-1}
      aria-hidden
      className="card__photo mat-photo"
      onPointerEnter={(e) => e.pointerType === "mouse" && hoverImage && setWarm(true)}
    >
      <ProductImage src={image} alt="" focal={focal} sizes={sizes} priority={priority} eager={eager} lowPriority={eager} className="card__img" />
      {warm && hoverImage && hoverImage !== image && (
        <ProductImage src={hoverImage} alt="" sizes={sizes} className="card__img card__img--hover" />
      )}
      {tags.length > 0 && (
        <span className="card__tags">
          {tags.map((t) => (
            <span key={t} className="tag" data-kind={t === "soldout" ? "soldout" : t}>
              {t === "soldout" ? "Нет в наличии" : BADGE_LABEL[t]}
            </span>
          ))}
        </span>
      )}
    </Link>
  );
}
