"use client";

import { X } from "lucide-react";
import { useModalDialog } from "@/components/ui/useModalDialog";
import { SearchBar } from "./SearchBar";
import type { NavCategory } from "./nav";
import { useUi } from "./UiProvider";

/** Окно поиска: на планшете и десктопе — карточка под шапкой, на телефоне — на весь экран (см. .sheet[data-side="top"]). */
export function SearchDialog({ categories }: { categories: NavCategory[] }) {
  const { searchOpen, setSearchOpen } = useUi();
  const dialog = useModalDialog(searchOpen, () => setSearchOpen(false));
  return (
    <dialog {...dialog} aria-label="Поиск по каталогу" className="sheet" data-side="top">
      <div className="flex items-center justify-between px-4 pt-3 md:px-6 md:pt-4">
        <span className="font-display text-2xl">Поиск</span>
        <button type="button" className="icon-btn" aria-label="Закрыть поиск" onClick={() => setSearchOpen(false)}>
          <X aria-hidden className="size-6" strokeWidth={1.5} />
        </button>
      </div>
      {/* SearchBar монтируется только при открытом окне: поле получает фокус, прежний запрос не висит. */}
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-6 pt-2 md:px-6">
        {searchOpen && <SearchBar categories={categories} onNavigate={() => setSearchOpen(false)} />}
      </div>
    </dialog>
  );
}
