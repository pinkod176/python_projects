import type { Metadata } from "next";
import { FavoritesList } from "@/components/product/FavoritesList";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";

export const metadata: Metadata = { title: "Избранное", robots: { index: false } };

export default function FavoritesPage() {
  return (
    <div className="container-x pb-6 pt-8 md:pt-10">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "Избранное" }]} />
      <header className="reveal-load mb-10 mt-8 md:mb-14 md:mt-12">
        <p className="eyebrow">Сохранённое на этом устройстве</p>
        <h1 className="mt-3 text-h1 font-light">Избранное</h1>
      </header>
      <FavoritesList />
    </div>
  );
}
