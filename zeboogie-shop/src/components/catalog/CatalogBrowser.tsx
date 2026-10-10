"use client";

import { SlidersHorizontal, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { DEFAULT_PARAMS, toApiQuery, toPageQuery, type UiParams } from "@/lib/catalog/params";
import type { CatalogResult } from "@/lib/catalog/query";
import { plural } from "@/lib/format";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProductGrid } from "@/components/product/ProductGrid";
import { Filters } from "./Filters";

const PAGE_SIZE = 12;
const SORT_LABELS: Record<UiParams["sort"], string> = {
  new: "Сначала новые",
  "price-asc": "Сначала дешевле",
  "price-desc": "Сначала дороже",
  name: "По названию",
};

type Status = "idle" | "loading" | "more" | "error";

export function CatalogBrowser({ initial, initialParams }: { initial: CatalogResult; initialParams: UiParams }) {
  const [params, setParams] = useState(initialParams);
  const [data, setData] = useState(initial);
  const [status, setStatus] = useState<Status>("idle");
  const [panelOpen, setPanelOpen] = useState(false);
  const reqId = useRef(0);
  const first = useRef(true);

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

  // Любое изменение фильтров: обновляем адрес (без перезагрузки) и запрашиваем данные. Ввод цены/поиска — с задержкой.
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const t = setTimeout(() => {
      const qs = toPageQuery(params);
      window.history.replaceState(null, "", qs ? `/catalog?${qs}` : "/catalog");
      void fetchPage(params, 1, false);
    }, 250);
    return () => clearTimeout(t);
  }, [params, fetchPage]);

  const patch = (p: Partial<UiParams>) => setParams((cur) => ({ ...cur, ...p }));
  const dirty = JSON.stringify({ ...params, sort: "new", q: "" }) !== JSON.stringify({ ...DEFAULT_PARAMS });
  const reset = () => setParams((cur) => ({ ...DEFAULT_PARAMS, q: cur.q, sort: cur.sort }));
  const loading = status === "loading";
  const hasMore = data.items.length < data.total;

  const filters = <Filters facets={data.facets} params={params} onChange={patch} onReset={reset} dirty={dirty} />;

  return (
    <div className="grid gap-10 lg:grid-cols-[16rem_1fr] lg:gap-14">
      {/* Десктоп: боковая панель */}
      <aside aria-label="Фильтры" className="hidden lg:block">
        <div className="sticky top-28">{filters}</div>
      </aside>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-3 border-b border-line pb-4">
          <label className="flex min-w-0 flex-1 items-center border-b border-ink/40 focus-within:border-ink sm:max-w-sm">
            <span className="sr-only">Поиск по каталогу</span>
            <input
              type="search"
              value={params.q}
              onChange={(e) => patch({ q: e.target.value })}
              placeholder="Поиск по названию и описанию"
              className="min-h-11 w-full bg-transparent outline-none placeholder:text-ink-soft"
            />
          </label>
          <button type="button" className="btn btn-ghost !min-h-11 lg:hidden" onClick={() => setPanelOpen(true)}>
            <SlidersHorizontal aria-hidden className="size-4" /> Фильтры{dirty ? " •" : ""}
          </button>
          <label className="ml-auto flex items-center gap-2 text-sm">
            <span className="text-ink-soft">Сортировка</span>
            <select
              value={params.sort}
              onChange={(e) => patch({ sort: e.target.value as UiParams["sort"] })}
              className="field !min-h-11 !w-auto !py-1.5"
            >
              {Object.entries(SORT_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </label>
        </div>

        <p className="mt-4 text-sm text-ink-soft" aria-live="polite">
          {loading ? "Обновляем…" : `${data.total} ${plural(data.total, ["работа", "работы", "работ"])}`}
        </p>

        <div className={`mt-6 transition-opacity ${loading ? "opacity-50" : ""}`} aria-busy={loading}>
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
              action={<button type="button" className="btn btn-ghost" onClick={() => setParams(DEFAULT_PARAMS)}>Сбросить поиск и фильтры</button>}
            >
              Попробуйте изменить запрос или убрать часть фильтров.
            </EmptyState>
          ) : (
            <ProductGrid items={data.items} priorityCount={4} />
          )}
        </div>

        {hasMore && status !== "error" && (
          <div className="mt-14 flex flex-col items-center gap-3">
            <p className="text-sm text-ink-soft">Показано {data.items.length} из {data.total}</p>
            <button type="button" className="btn btn-ghost min-w-56" disabled={status === "more"} onClick={() => void fetchPage(params, data.page + 1, true)}>
              {status === "more" ? "Загружаем…" : "Показать ещё"}
            </button>
          </div>
        )}
      </div>

      {/* Мобильные фильтры */}
      {panelOpen && (
        <div role="dialog" aria-modal="true" aria-label="Фильтры" className="fixed inset-0 z-50 flex flex-col bg-paper lg:hidden">
          <div className="flex h-16 shrink-0 items-center justify-between border-b border-line px-4">
            <span className="font-serif text-2xl">Фильтры</span>
            <button type="button" aria-label="Закрыть фильтры" className="grid size-11 place-items-center" onClick={() => setPanelOpen(false)}>
              <X aria-hidden className="size-6" strokeWidth={1.5} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">{filters}</div>
          <div className="shrink-0 border-t border-line p-4">
            <button type="button" className="btn btn-solid w-full" onClick={() => setPanelOpen(false)}>
              Показать {data.total} {plural(data.total, ["работу", "работы", "работ"])}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
