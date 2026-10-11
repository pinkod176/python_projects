import type { Metadata } from "next";
import { CheckoutFlow } from "@/components/checkout/CheckoutFlow";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";

export const metadata: Metadata = { title: "Оформление заказа", robots: { index: false } };

export default function CheckoutPage() {
  return (
    <div className="container-x pb-6 pt-2 md:pt-4">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "Корзина", href: "/cart" }, { label: "Оформление заказа" }]} />
      <header className="page-head reveal-load">
        <h1 className="page-title">Оформление заказа</h1>
      </header>
      <CheckoutFlow />
    </div>
  );
}
