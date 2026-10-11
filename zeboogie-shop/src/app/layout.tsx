import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { brand } from "@/content/brand";
import { CartDrawer } from "@/components/cart/CartDrawer";
import { CartProvider } from "@/components/cart/CartProvider";
import { DemoBanner } from "@/components/layout/DemoBanner";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { MobileMenu } from "@/components/layout/MobileMenu";
import { QuickBar } from "@/components/layout/QuickBar";
import { QuickViewProvider } from "@/components/product/QuickView";
import { SearchDialog } from "@/components/layout/SearchDialog";
import { UiProvider } from "@/components/layout/UiProvider";
import { buildNav } from "@/components/layout/nav";
import { NavBoot } from "@/components/ui/NavBoot";
import { RevealBoot } from "@/components/ui/Reveal";
import { getCatalogState } from "@/lib/catalog/service";
import { getEnv, isDemo } from "@/lib/config/env";

// Каталог читается из снимка при каждом запросе: страницы не «замораживаются» на момент сборки.
export const dynamic = "force-dynamic";

export function generateMetadata(): Metadata {
  const env = getEnv();
  return {
    metadataBase: new URL(env.SITE_URL),
    title: { default: `${brand.name} — ${brand.tagline}`, template: `%s · ${brand.name}` },
    description: brand.lead,
    openGraph: { type: "website", siteName: `${brand.name} ${brand.descriptor}`, locale: "ru_RU" },
    // Тестовые данные не должны попадать в поисковую выдачу.
    robots: isDemo() ? { index: false, follow: false } : undefined,
  };
}

// viewportFit: "cover" — страница занимает весь экран телефона, отступы под «чёлку» и полоску жестов берут на себя env(safe-area-inset-*).
export const viewport: Viewport = { themeColor: "#f1eae0", width: "device-width", initialScale: 1, viewportFit: "cover" };

export default async function RootLayout({ children }: { children: ReactNode }) {
  const state = await getCatalogState();
  const collections = state.status === "ok" ? state.catalog.collections : [];
  const shop = state.status === "ok" ? state.catalog.shop : null;
  const nav = buildNav(collections);
  return (
    <html lang="ru" data-scroll-behavior="smooth">
      <body data-demo={isDemo() ? "" : undefined}>
        <CartProvider>
          <UiProvider>
           <QuickViewProvider>
            <RevealBoot />
            <NavBoot />
            <a href="#content" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:bg-ink focus:px-4 focus:py-3 focus:text-paper">
              К содержимому
            </a>
            {isDemo() && <DemoBanner />}
            <Header collections={collections} />
            <main id="content">{children}</main>
            <Footer collections={collections} shop={shop} />
            <QuickBar />
            <MobileMenu tabs={nav.tabs} categories={nav.categories} />
            <SearchDialog categories={nav.categories} />
            <CartDrawer />
           </QuickViewProvider>
          </UiProvider>
        </CartProvider>
      </body>
    </html>
  );
}
