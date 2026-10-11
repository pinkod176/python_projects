import type { Metadata } from "next";
import { ExternalLink, Mail, MessageCircle, Phone, Users } from "lucide-react";
import { brand } from "@/content/brand";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Reveal } from "@/components/ui/Reveal";
import { getCatalogState } from "@/lib/catalog/service";
import { getEnv } from "@/lib/config/env";

export const metadata: Metadata = { title: "Контакты", description: "Как связаться с мастерской Zeboogie." };

const card = "group flex min-h-[5.5rem] items-center gap-5 rounded-lg border border-line bg-paper-2 p-5 transition-[transform,background-color] duration-300 ease-soft active:scale-[0.99] active:bg-paper-3 hover:-translate-y-0.5 hover:bg-paper";

export default async function ContactsPage() {
  const state = await getCatalogState();
  const shop = state.status === "ok" ? state.catalog.shop : null;
  const { SHOP_EMAIL, SHOP_PHONE } = getEnv();

  type Item = { href: string; icon: typeof Mail; title: string; text: string; external?: boolean };
  const items: Item[] = [];
  if (shop) {
    items.push({ href: shop.messageUrl, icon: MessageCircle, title: "Написать мастерам", text: "Личные сообщения ВКонтакте — самый быстрый способ", external: true });
    items.push({ href: shop.url, icon: Users, title: "Сообщество ВКонтакте", text: "Новые работы и жизнь мастерской", external: true });
  }
  if (SHOP_EMAIL) items.push({ href: `mailto:${SHOP_EMAIL}`, icon: Mail, title: SHOP_EMAIL, text: "Электронная почта" });
  if (SHOP_PHONE) items.push({ href: `tel:${SHOP_PHONE.replace(/[^\d+]/g, "")}`, icon: Phone, title: SHOP_PHONE, text: "Телефон" });

  return (
    <div className="container-x pb-6 pt-6 md:pt-8">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "Контакты" }]} />
      <header className="mt-6 md:mt-8">
        <Reveal first>
          <p className="eyebrow">{brand.name} · {brand.descriptor}</p>
          <h1 className="mt-3 text-h1 font-light">Контакты</h1>
        </Reveal>
        <Reveal first delay={100}>
          <p className="mt-6 max-w-2xl text-lead text-ink-soft">
            Мастерская работает с {brand.since} года. Заказы и вопросы принимаем сообщениями — отвечаем лично.
          </p>
        </Reveal>
      </header>

      <ul className="mt-12 grid gap-4 md:mt-16 md:grid-cols-2">
        {items.map((it, i) => (
          <Reveal key={it.href} as="li" delay={(i % 2) * 90}>
            <a href={it.href} className={card} {...(it.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
              <span className="grid size-12 shrink-0 place-items-center rounded-full bg-paper text-copper">
                <it.icon aria-hidden className="size-6" strokeWidth={1.4} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-display text-2xl leading-tight">{it.title}</span>
                <span className="mt-1 block text-sm text-ink-soft">{it.text}</span>
              </span>
              {it.external && <ExternalLink aria-hidden className="size-4 shrink-0 text-ink-soft" strokeWidth={1.5} />}
            </a>
          </Reveal>
        ))}
      </ul>
      {items.length === 0 && <p className="mt-12 text-ink-soft">Контакты появятся, когда будет подключено сообщество.</p>}
    </div>
  );
}
