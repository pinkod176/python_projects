import type { Metadata } from "next";
import { CheckoutFlow } from "@/components/checkout/CheckoutFlow";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";

export const metadata: Metadata = { title: "Оформление заказа", robots: { index: false } };

export default function CheckoutPage() {
  return (
    <div className="container-x py-8 md:py-12">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "Оформление заказа" }]} />
      <h1 className="mb-10 mt-6 text-5xl md:text-7xl">Заказ</h1>
      <CheckoutFlow />
    </div>
  );
}
