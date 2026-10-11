import type { Metadata } from "next";
import { CartView } from "@/components/cart/CartView";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";

export const metadata: Metadata = { title: "Корзина", robots: { index: false } };

export default function CartPage() {
  return (
    <div className="container-x pb-6 pt-2 md:pt-4">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "Корзина" }]} />
      <header className="page-head reveal-load">
        <h1 className="page-title">Корзина</h1>
      </header>
      <CartView />
    </div>
  );
}
