import Image from "next/image";
import { ImageOff } from "lucide-react";

type Props = {
  src: string | null | undefined;
  alt: string;
  sizes: string;
  priority?: boolean;
  className?: string;
};

/** Фото товара с фиксированным соотношением сторон (без скачков вёрстки) и заглушкой, если фото нет. */
export function ProductImage({ src, alt, sizes, priority, className = "" }: Props) {
  if (!src) {
    return (
      <div role="img" aria-label={alt} className={`grid h-full w-full place-items-center bg-paper-3 text-ink-soft ${className}`}>
        <ImageOff aria-hidden className="size-8" strokeWidth={1.25} />
      </div>
    );
  }
  return (
    <Image
      src={src}
      alt={alt}
      fill
      sizes={sizes}
      priority={priority}
      className={`object-cover ${className}`}
    />
  );
}
