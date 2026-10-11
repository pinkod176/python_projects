/**
 * Возврат из карточки товара в каталог: сохраняем, сколько страниц «Показать ещё» было загружено и где стоял экран,
 * и после нажатия «Назад» дозагружаем те же страницы и возвращаем прокрутку. Фильтры и сортировка и так лежат в адресе (URL).
 * Состояние живёт в sessionStorage вкладки; восстанавливается только после перехода «назад/вперёд», а не при обычном заходе в каталог.
 */
const KEY = "zeboogie:catalog-restore";
const MAX_AGE_MS = 30 * 60_000;

export type CatalogRestore = { key: string; pages: number; y: number; at: number };

export function saveCatalogRestore(state: Omit<CatalogRestore, "at">) {
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify({ ...state, at: Date.now() } satisfies CatalogRestore));
  } catch {
    /* приватный режим — просто не восстановим */
  }
}

export function loadCatalogRestore(key: string): CatalogRestore | null {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as CatalogRestore;
    return s.key === key && Date.now() - s.at < MAX_AGE_MS ? s : null;
  } catch {
    return null;
  }
}

declare global {
  interface Window {
    __zbPop?: number;
  }
}

/** Был ли переход «назад/вперёд» только что (отметку ставит NavBoot на событие popstate). */
export function justNavigatedBack(): boolean {
  if (typeof window === "undefined") return false;
  if (window.__zbPop !== undefined && performance.now() - window.__zbPop < 4000) return true;
  const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
  return nav?.type === "back_forward";
}
