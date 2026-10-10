import type { Metadata } from "next";
import { FavoritesList } from "@/components/product/FavoritesList";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";

export const metadata: Metadata = { title: "Избранное", robots: { index: false } };

export default function FavoritesPage() {
  return (
    <div className="container-x py-8 md:py-12">
      <Breadcrumbs items={[{ label: "Главная", href: "/" }, { label: "Избранное" }]} />
      <h1 className="mb-10 mt-6 text-5xl md:text-7xl">Избранное</h1>
      <FavoritesList />
    </div>
  );
}
