import Link from "next/link";
import { brand } from "@/content/brand";
import { getEnv } from "@/lib/config/env";
import type { Collection, ShopInfo } from "@/lib/types";
import { Reveal } from "@/components/ui/Reveal";

const link = "u-link inline-flex min-h-10 items-center text-on-accent-soft";

export function Footer({ collections, shop }: { collections: Collection[]; shop: ShopInfo | null }) {
  const { SHOP_EMAIL, SHOP_PHONE } = getEnv();
  return (
    <footer className="footer on-dark mt-24 bg-footer text-on-accent md:mt-32">
      <Reveal className="container-x grid gap-16 py-16 md:grid-cols-12 md:py-24">
        <div className="md:col-span-5">
          <p className="font-display text-5xl font-light tracking-[-0.02em] md:text-6xl">{brand.name}</p>
          <p className="mt-2 text-xs uppercase tracking-[0.24em] text-on-accent-soft">{brand.descriptor}</p>
          <p className="mt-8 max-w-sm font-display text-2xl italic leading-snug text-on-accent-soft">{brand.pullQuote}</p>
        </div>
        <nav aria-label="Разделы" className="md:col-span-3">
          <p className="text-xs uppercase tracking-[0.18em] text-on-accent-soft">Каталог</p>
          <ul className="mt-4 space-y-1">
            <li><Link className={link} href="/catalog">Все работы</Link></li>
            {collections.map((c) => (
              <li key={c.id}><Link className={link} href={`/catalog?category=${c.id}`}>{c.title}</Link></li>
            ))}
            {brand.nav.info.map((i) => (
              <li key={i.href}><Link className={link} href={i.href}>{i.label}</Link></li>
            ))}
            <li><Link className={link} href="/favorites">Избранное</Link></li>
          </ul>
        </nav>
        <div className="md:col-span-4">
          <p className="text-xs uppercase tracking-[0.18em] text-on-accent-soft">Связаться</p>
          <ul className="mt-4 space-y-1">
            {shop && (
              <>
                <li><a className={link} href={shop.messageUrl} target="_blank" rel="noopener noreferrer">Написать мастерам ВКонтакте</a></li>
                <li><a className={link} href={shop.url} target="_blank" rel="noopener noreferrer">Сообщество ВКонтакте</a></li>
              </>
            )}
            {SHOP_EMAIL && <li><a className={link} href={`mailto:${SHOP_EMAIL}`}>{SHOP_EMAIL}</a></li>}
            {SHOP_PHONE && <li><a className={link} href={`tel:${SHOP_PHONE.replace(/[^\d+]/g, "")}`}>{SHOP_PHONE}</a></li>}
          </ul>
        </div>
      </Reveal>
      <div className="border-t border-on-accent/15">
        <p className="container-x py-6 text-xs text-on-accent-soft">
          © {new Date().getFullYear()} {brand.name} · {brand.descriptor}. Мастерская с {brand.since} года.
        </p>
      </div>
    </footer>
  );
}
