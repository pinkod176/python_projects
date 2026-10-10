import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { brand } from "@/content/brand";
import { CartDrawer } from "@/components/cart/CartDrawer";
import { CartProvider } from "@/components/cart/CartProvider";
import { DemoBanner } from "@/components/layout/DemoBanner";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
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

export const viewport: Viewport = { themeColor: "#f1eae0", width: "device-width", initialScale: 1 };

export default async function RootLayout({ children }: { children: ReactNode }) {
  const state = await getCatalogState();
  const collections = state.status === "ok" ? state.catalog.collections : [];
  const shop = state.status === "ok" ? state.catalog.shop : null;
  return (
    <html lang="ru" data-scroll-behavior="smooth">
      <body>
        <CartProvider>
          <RevealBoot />
          <a href="#content" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:bg-ink focus:px-4 focus:py-3 focus:text-paper">
            К содержимому
          </a>
          {isDemo() && <DemoBanner />}
          <Header collections={collections} />
          <main id="content">{children}</main>
          <Footer collections={collections} shop={shop} />
          <CartDrawer />
        </CartProvider>
      </body>
    </html>
  );
}
