"use client";

import { ChevronDown, Grid2x2, SlidersHorizontal, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { DEFAULT_PARAMS, toApiQuery, toPageQuery, type UiParams } from "@/lib/catalog/params";
import type { CatalogResult } from "@/lib/catalog/query";
import { loadCatalogRestore, justNavigatedBack, saveCatalogRestore } from "@/lib/catalog/restore";
import { plural } from "@/lib/format";
import { usePref, setPref } from "@/lib/use-pref";
import { useMedia } from "@/lib/use-media";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProductGrid, ProductGridSkeleton } from "@/components/product/ProductGrid";
import { ActiveFilters } from "./ActiveFilters";
import { CategoryPills } from "./CategoryPills";
import { FilterSheet } from "./FilterSheet";
import { Filters } from "./Filters";

const PAGE_SIZE = 12;
type Status = "idle" | "loading" | "more" | "error";

const sortLabels = (hasPopularity: boolean, current: UiParams["sort"]): [UiParams["sort"], string][] => [
  ["new", "Сначала новые"],
  ["price-asc", "Цена по возрастанию"],
  ["price-desc", "Цена по убыванию"],
  // Без лайков VK это «выбор мастерской» (работы из hero, затем новые): называем честно.
  ["popular", hasPopularity ? "Популярные" : "Выбор мастерской"],
  ...(current === "name" ? ([["name", "По названию"]] as [UiParams["sort"], string][]) : []),
];

export function CatalogBrowser({ initial, initialParams }: { initial: CatalogResult; initialParams: UiParams }) {
  const [params, setParams] = useState(initialParams);
  const [data, setData] = useState(initial);
  const [status, setStatus] = useState<Status>("idle");
  const [sheetOpen, setSheetOpen] = useState(false);
  const view = usePref("zb:view", "grid") === "large" ? "large" : "grid";
  const sidebarPref = usePref("zb:sidebar", "open") !== "closed";
  const isWide = useMedia("(min-width: 1200px)");
  const reqId = useRef(0);
  const live = useRef({ key: toPageQuery(initialParams), pages: initial.page });

  const fetchPage = useCallback(async (p: UiParams, page: number, append: boolean) => {
    const id = ++reqId.current;
    setStatus(append ? "more" : "loading");
    try {
      const res = await fetch(`/api/catalog?${toApiQuery(p, page, PAGE_SIZE)}`);
      if (!res.ok) throw new Error(String(res.status));
      const json = (await res.json()) as CatalogResult;
      if (id !== reqId.current) return; // устаревший ответ
      setData((prev) => (append ? { ...json, items: [...prev.items, ...json.items] } : json));
      setStatus("idle");
    } catch {
      if (id === reqId.current) setStatus("error");
    }
  }, []);

  // Любое изменение фильтров: обновляем адрес (без перезагрузки) и запрашиваем данные. Ввод цены — с задержкой.
  // Сравниваем с уже загруженным запросом, а не «пропускаем первый запуск»: так двойной запуск эффектов в dev (StrictMode)
  // не перезагружает список и не затирает дозагруженные страницы.
  const loadedKey = useRef(toPageQuery(initialParams));
  useEffect(() => {
    const qs = toPageQuery(params);
    if (qs === loadedKey.current) return;
    const t = setTimeout(() => {
      loadedKey.current = qs;
      live.current = { key: qs, pages: 1 };
      window.history.replaceState(window.history.state, "", qs ? `/catalog?${qs}` : "/catalog");
      void fetchPage(params, 1, false);
    }, 250);
    return () => clearTimeout(t);
  }, [params, fetchPage]);

  useEffect(() => {
    live.current.pages = data.page;
  }, [data.page]);

  // Возврат из карточки товара: дозагружаем те же страницы и возвращаем прокрутку; пока листаем — помним, где мы.
  useEffect(() => {
    let timer = 0;
    // Не перезаписываем сохранённое после ухода со страницы: роутер сбрасывает прокрутку в 0 уже на адресе товара.
    const save = () => {
      if (window.location.pathname === "/catalog") saveCatalogRestore({ key: live.current.key, pages: live.current.pages, y: window.scrollY });
    };
    const onScroll = () => {
      if (!timer) timer = window.setTimeout(() => { timer = 0; save(); }, 250);
    };
    window.addEventListener("scroll", onScroll, { passive: true });

    let cancelled = false;
    const saved = justNavigatedBack() ? loadCatalogRestore(toPageQuery(initialParams)) : null;
    if (saved && (saved.pages > 1 || saved.y > 40)) {
      void (async () => {
        try {
          const pages = Math.min(saved.pages, 10);
          const more = await Promise.all(
            Array.from({ length: pages - 1 }, (_, i) =>
              fetch(`/api/catalog?${toApiQuery(initialParams, i + 2, PAGE_SIZE)}`).then((r) => (r.ok ? (r.json() as Promise<CatalogResult>) : Promise.reject(new Error(String(r.status))))),
            ),
          );
          if (cancelled) return;
          if (more.length) setData((prev) => ({ ...prev, page: pages, items: [...prev.items, ...more.flatMap((m) => m.items)] }));
        } catch {
          /* вернём только прокрутку */
        }
        if (cancelled) return;
        // Роутер Next после перехода «назад» сам может прокрутить страницу вверх уже после нашей прокрутки,
        // поэтому возвращаем позицию несколько раз, пока человек сам не начал листать.
        let touched = false;
        const stop = () => { touched = true; };
        for (const ev of ["wheel", "touchstart", "keydown", "pointerdown"] as const) window.addEventListener(ev, stop, { once: true, passive: true });
        const apply = () => {
          if (!touched && Math.abs(window.scrollY - saved.y) > 24) window.scrollTo({ top: saved.y, behavior: "instant" });
        };
        requestAnimationFrame(() => requestAnimationFrame(apply));
        for (const ms of [120, 350, 800, 1500]) window.setTimeout(apply, ms);
      })();
    }
    return () => {
      cancelled = true;
      window.removeEventListener("scroll", onScroll);
      if (timer) window.clearTimeout(timer);
    };
    // Выполняется один раз при открытии каталога.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const patch = (p: Partial<UiParams>) => setParams((cur) => ({ ...cur, ...p }));
  const resetAll = () => setParams((cur) => ({ ...DEFAULT_PARAMS, sort: cur.sort }));
  const loading = status === "loading";
  const hasMore = data.items.length < data.total;
  const f = data.facets;
  const hasFilters = Boolean((f.price && f.price.points.length > 1) || f.hasAvailabilityData || f.attributes.length > 0);
  const activeCount = (params.category ? 1 : 0) + (params.min || params.max ? 1 : 0) + (params.inStock ? 1 : 0) + params.attrs.length + (params.q.trim() ? 1 : 0);
  const sidebarOpen = hasFilters && sidebarPref;

  const onFiltersClick = () => {
    if (isWide) setPref("zb:sidebar", sidebarPref ? "closed" : "open");
    else setSheetOpen(true);
  };

  const title = f.categories.find((c) => c.id === params.category)?.title ?? "Каталог";

  return (
    <div>
      <div className="catalog-top">
        <header className="catalog-head">
          <h1 className="page-title">{title}</h1>
          <p className="catalog-count" aria-live="polite">
            {loading ? "Обновляем…" : <><strong>{data.total}</strong> {plural(data.total, ["работа", "работы", "работ"])}</>}
          </p>
        </header>
        <div className="catalog-pills">
          <CategoryPills categories={f.categories} value={params.category} onChange={(category) => patch({ category })} />
        </div>
        {(hasFilters || f.categories.length > 0) && (
          <button
            type="button"
            className="btn btn-ghost btn-sm catalog-filters-btn"
            aria-expanded={isWide ? sidebarOpen : sheetOpen}
            aria-controls={isWide ? "catalog-filters" : undefined}
            aria-haspopup={isWide ? undefined : "dialog"}
            onClick={onFiltersClick}
          >
            <SlidersHorizontal aria-hidden className="size-4" strokeWidth={1.75} />
            Фильтры
            {activeCount > 0 && <span className="badge">{activeCount}</span>}
          </button>
        )}
        <label className="catalog-sort">
          <span className="sr-only">Сортировка</span>
          <select value={params.sort} onChange={(e) => patch({ sort: e.target.value as UiParams["sort"] })}>
            {sortLabels(f.hasPopularity, params.sort).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
          <ChevronDown aria-hidden className="size-4" strokeWidth={1.5} />
        </label>
        <div className="seg" role="group" aria-label="Вид сетки">
          <button type="button" aria-pressed={view === "grid"} aria-label="Обычные карточки" onClick={() => setPref("zb:view", "grid")}>
            <Grid2x2 aria-hidden className="size-[1.15rem]" strokeWidth={1.5} />
          </button>
          <button type="button" aria-pressed={view === "large"} aria-label="Крупные карточки" onClick={() => setPref("zb:view", "large")}>
            <Square aria-hidden className="size-[1.15rem]" strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {activeCount > 0 && (
        <div className="mt-3">
          <ActiveFilters facets={f} params={params} onChange={patch} onResetAll={resetAll} />
        </div>
      )}

      <div className="catalog mt-6" data-sidebar={sidebarOpen ? "open" : "closed"}>
        <aside id="catalog-filters" className="catalog__side" aria-label="Фильтры">
          <div className="catalog__side-inner">
            <Filters facets={f} params={params} onChange={patch} />
          </div>
        </aside>

        <div
          className="min-w-0"
          onClickCapture={(e) => {
            // Уходим на страницу товара — запоминаем, сколько страниц загружено и где стоит экран.
            if ((e.target as Element).closest('a[href^="/product/"]')) {
              saveCatalogRestore({ key: live.current.key, pages: live.current.pages, y: window.scrollY });
            }
          }}
        >
          <div className={`transition-opacity duration-300 ${loading ? "opacity-50" : ""}`} aria-busy={loading}>
            {status === "error" ? (
              <EmptyState
                title="Не удалось загрузить товары"
                action={<button type="button" className="btn btn-solid" onClick={() => void fetchPage(params, 1, false)}>Повторить</button>}
              >
                Проверьте соединение и попробуйте снова.
              </EmptyState>
            ) : data.items.length === 0 && !loading ? (
              <EmptyState
                title="Ничего не нашлось"
                action={<button type="button" className="btn btn-solid" onClick={() => setParams({ ...DEFAULT_PARAMS, sort: params.sort })}>Сбросить поиск и фильтры</button>}
              >
                Попробуйте изменить запрос или убрать часть фильтров.
              </EmptyState>
            ) : (
              <ProductGrid items={data.items} priorityCount={4} firstRow headingLevel={2} view={view} sidebar={sidebarOpen} />
            )}
            {status === "more" && (
              <div className="mt-10">
                <ProductGridSkeleton count={4} view={view} />
              </div>
            )}
          </div>

          {hasMore && status !== "error" && (
            <div className="mt-16 flex flex-col items-center gap-3">
              <p className="text-sm text-ink-soft">Показано {data.items.length} из {data.total}</p>
              <div className="more-progress" aria-hidden>
                <span style={{ transform: `scaleX(${data.items.length / data.total})` }} />
              </div>
              <button type="button" className="btn btn-ghost mt-2 min-w-60" disabled={status === "more"} onClick={() => void fetchPage(params, data.page + 1, true)}>
                {status === "more" ? "Загружаем…" : "Показать ещё"}
              </button>
            </div>
          )}
        </div>
      </div>

      <FilterSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        total={data.total}
        loading={loading}
        facets={f}
        params={params}
        onChange={patch}
        onResetAll={resetAll}
        dirty={activeCount > 0}
      />
    </div>
  );
}
