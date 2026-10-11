"use client";

import { usePathname } from "next/navigation";
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

/**
 * Состояние оболочки сайта, которым пользуются сразу несколько кусков интерфейса (шапка, нижняя панель, меню, поиск).
 * Меню и поиск «помнят», на какой странице их открыли, и сами считаются закрытыми после перехода на другую страницу
 * (кнопка «Назад», ссылка в меню) — без эффектов и без залипших оверлеев, перекрывающих кнопки.
 */
type Ui = {
  menuOpen: boolean;
  setMenuOpen: (v: boolean) => void;
  searchOpen: boolean;
  setSearchOpen: (v: boolean) => void;
};

const UiContext = createContext<Ui | null>(null);

export function UiProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [menuAt, setMenuAt] = useState<string | null>(null);
  const [searchAt, setSearchAt] = useState<string | null>(null);
  const value = useMemo<Ui>(
    () => ({
      menuOpen: menuAt === pathname,
      setMenuOpen: (v) => setMenuAt(v ? pathname : null),
      searchOpen: searchAt === pathname,
      setSearchOpen: (v) => setSearchAt(v ? pathname : null),
    }),
    [menuAt, searchAt, pathname],
  );
  return <UiContext.Provider value={value}>{children}</UiContext.Provider>;
}

export function useUi(): Ui {
  const ctx = useContext(UiContext);
  if (!ctx) throw new Error("useUi используется вне UiProvider");
  return ctx;
}
