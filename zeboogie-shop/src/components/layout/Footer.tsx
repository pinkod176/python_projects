import Link from "next/link";
import { brand } from "@/content/brand";
import { getEnv } from "@/lib/config/env";
import type { Collection, ShopInfo } from "@/lib/types";

export function Footer({ collections, shop }: { collections: Collection[]; shop: ShopInfo | null }) {
  const { SHOP_EMAIL, SHOP_PHONE } = getEnv();
  return (
    <footer className="mt-24 border-t border-line bg-ink text-paper md:mt-32">
      <div className="container-x grid gap-12 py-14 md:grid-cols-12 md:py-20">
        <div className="md:col-span-5">
          <p className="font-serif text-4xl md:text-5xl">{brand.name}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-paper/60">{brand.descriptor}</p>
          <p className="mt-6 max-w-sm text-paper/75">{brand.manifesto}</p>
        </div>
        <nav aria-label="Разделы" className="md:col-span-3">
          <p className="text-xs uppercase tracking-[0.18em] text-paper/60">Каталог</p>
          <ul className="mt-4 space-y-1">
            <li><Link className="inline-flex min-h-9 items-center hover:underline" href="/catalog">Все работы</Link></li>
            {collections.map((c) => (
              <li key={c.id}>
                <Link className="inline-flex min-h-9 items-center hover:underline" href={`/catalog?category=${c.id}`}>{c.title}</Link>
              </li>
            ))}
            <li><Link className="inline-flex min-h-9 items-center hover:underline" href="/about">О мастерской</Link></li>
            <li><Link className="inline-flex min-h-9 items-center hover:underline" href="/favorites">Избранное</Link></li>
          </ul>
        </nav>
        <div className="md:col-span-4">
          <p className="text-xs uppercase tracking-[0.18em] text-paper/60">Связаться</p>
          <ul className="mt-4 space-y-1">
            {shop && (
              <>
                <li><a className="inline-flex min-h-9 items-center hover:underline" href={shop.messageUrl} target="_blank" rel="noopener noreferrer">Написать мастерам ВКонтакте</a></li>
                <li><a className="inline-flex min-h-9 items-center hover:underline" href={shop.url} target="_blank" rel="noopener noreferrer">Сообщество ВКонтакте</a></li>
              </>
            )}
            {SHOP_EMAIL && <li><a className="inline-flex min-h-9 items-center hover:underline" href={`mailto:${SHOP_EMAIL}`}>{SHOP_EMAIL}</a></li>}
            {SHOP_PHONE && <li><a className="inline-flex min-h-9 items-center hover:underline" href={`tel:${SHOP_PHONE.replace(/[^\d+]/g, "")}`}>{SHOP_PHONE}</a></li>}
          </ul>
        </div>
      </div>
      <div className="border-t border-paper/15">
        <p className="container-x py-5 text-xs text-paper/60">
          © {new Date().getFullYear()} {brand.name} · {brand.descriptor}. Мастерская с {brand.since} года.
        </p>
      </div>
    </footer>
  );
}
