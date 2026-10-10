import type { Metadata } from "next";
import { CheckoutFlow } from "@/components/checkout/CheckoutFlow";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";

export const metadata: Metadata = { title: "Оформление заказа", robots: { index: false } };

export default function CheckoutPage() {
  return (
    <div className="container-x pb-6 pt-8 md:pt-10">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "Оформление заказа" }]} />
      <header className="reveal-load mb-10 mt-8 md:mb-14 md:mt-12">
        <p className="eyebrow">Почти готово</p>
        <h1 className="mt-3 text-h1 font-light">Оформление заказа</h1>
      </header>
      <CheckoutFlow />
    </div>
  );
}
