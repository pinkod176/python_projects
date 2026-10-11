import type { Metadata } from "next";
import { FavoritesList } from "@/components/product/FavoritesList";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";

export const metadata: Metadata = { title: "Избранное", robots: { index: false } };

export default function FavoritesPage() {
  return (
    <div className="container-x pb-6 pt-2 md:pt-4">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "Избранное" }]} />
      <header className="page-head reveal-load">
        <h1 className="page-title">Избранное</h1>
        <p className="eyebrow">Сохранено на этом устройстве</p>
      </header>
      <FavoritesList />
    </div>
  );
}
