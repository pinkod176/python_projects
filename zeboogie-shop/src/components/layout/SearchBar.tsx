"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Search } from "lucide-react";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import type { SearchSuggestions } from "@/app/api/search/route";
import { ProductImage } from "@/components/ui/ProductImage";
import { formatMoney, plural } from "@/lib/format";
import type { NavCategory } from "./nav";

type Props = { categories: NavCategory[]; onNavigate: () => void };

/**
 * Поиск с подсказками: подходящие подборки и работы с фото. Данные приходят из внутреннего API (/api/search), не из VK.
 * Клавиатура: ↓/↑ перемещают по подсказкам, Enter открывает выбранное или ищет по введённому, Esc закрывает окно (его обрабатывает <dialog>).
 */
export function SearchBar({ categories, onNavigate }: Props) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [result, setResult] = useState<{ q: string; data: SearchSuggestions } | null>(null);
  const [failed, setFailed] = useState(false);
  const listId = useId();
  const abort = useRef<AbortController | null>(null);
  const root = useRef<HTMLDivElement>(null);

  const term = q.trim();
  useEffect(() => {
    if (term.length < 2) return;
    const t = setTimeout(async () => {
      abort.current?.abort();
      abort.current = new AbortController();
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(term)}`, { signal: abort.current.signal });
        if (!res.ok) throw new Error(String(res.status));
        setResult({ q: term, data: (await res.json()) as SearchSuggestions });
        setFailed(false);
      } catch (e) {
        if ((e as Error).name !== "AbortError") setFailed(true);
      }
    }, 180);
    return () => clearTimeout(t);
  }, [term]);

  const data = term.length >= 2 && result?.q === term ? result.data : null;
  const pending = term.length >= 2 && !data && !failed;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    router.push(term ? `/catalog?q=${encodeURIComponent(term)}` : "/catalog");
    onNavigate();
  }

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    const items = [...(root.current?.querySelectorAll<HTMLElement>("[data-nav]") ?? [])];
    const i = items.indexOf(document.activeElement as HTMLElement);
    const next = e.key === "ArrowDown" ? Math.min(items.length - 1, i + 1) : Math.max(0, i - 1);
    if (items[next]) {
      e.preventDefault();
      items[next].focus();
    }
  }

  const categoryHit = (c: NavCategory) => (
    <li key={c.id}>
      <Link href={`/catalog?category=${c.id}`} onClick={onNavigate} data-nav className="search-hit">
        <span className="search-hit__photo"><ProductImage src={c.image} alt="" focal={c.imageFocal} sizes="52px" /></span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-display text-xl leading-tight">{c.title}</span>
          <span className="block text-xs text-ink-soft">{c.count} {plural(c.count, ["работа", "работы", "работ"])}</span>
        </span>
        <ArrowRight aria-hidden className="size-4 shrink-0 text-ink-soft" strokeWidth={1.5} />
      </Link>
    </li>
  );

  return (
    <div ref={root} onKeyDown={onKeyDown}>
      <form onSubmit={submit} role="search" className="flex items-stretch gap-2">
        <div className="relative min-w-0 flex-1">
          <Search aria-hidden className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-ink-soft" strokeWidth={1.5} />
          <label htmlFor={`${listId}-input`} className="sr-only">Поиск по каталогу</label>
          <input
            id={`${listId}-input`}
            data-nav
            data-autofocus
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Рамка, брошь, арт-объект…"
            autoComplete="off"
            enterKeyHint="search"
            aria-controls={listId}
            className="field pl-12"
          />
        </div>
        <button type="submit" className="btn btn-solid !px-5">Найти</button>
      </form>

      <div id={listId} className="mt-4" aria-live="polite">
        {term.length < 2 && categories.length > 0 && (
          <>
            <p className="eyebrow mb-1">Разделы</p>
            <ul className="divide-y divide-line">{categories.map(categoryHit)}</ul>
          </>
        )}
        {pending && <p className="py-6 text-sm text-ink-soft">Ищем…</p>}
        {failed && <p className="py-6 text-sm text-danger">Не удалось получить подсказки. Нажмите «Найти» — поиск сработает в каталоге.</p>}
        {data && data.categories.length > 0 && (
          <>
            <p className="eyebrow mb-1">Разделы</p>
            <ul className="divide-y divide-line">{data.categories.map(categoryHit)}</ul>
          </>
        )}
        {data && data.products.length > 0 && (
          <>
            <p className="eyebrow mb-1 mt-4">Работы</p>
            <ul className="divide-y divide-line">
              {data.products.map((p) => (
                <li key={p.vkId}>
                  <Link href={`/product/${p.slug}`} onClick={onNavigate} data-nav className="search-hit">
                    <span className="search-hit__photo"><ProductImage src={p.image} alt="" focal={p.focalPoint} sizes="52px" /></span>
                    <span className="min-w-0 flex-1">
                      <span className="line-clamp-2 leading-snug">{p.title}</span>
                      {p.categoryTitle && <span className="block truncate text-xs text-ink-soft">{p.categoryTitle}</span>}
                    </span>
                    {p.price && <span className="shrink-0 text-sm tabular-nums text-ink-soft">{formatMoney(p.price)}</span>}
                  </Link>
                </li>
              ))}
            </ul>
            {data.total > data.products.length && (
              <Link href={`/catalog?q=${encodeURIComponent(term)}`} onClick={onNavigate} data-nav className="u-link mt-4 inline-flex min-h-11 items-center gap-2 text-sm">
                Показать все {data.total} {plural(data.total, ["работу", "работы", "работ"])} <ArrowRight aria-hidden className="size-4" />
              </Link>
            )}
          </>
        )}
        {data && data.products.length === 0 && data.categories.length === 0 && (
          <p className="py-6 text-ink-soft">По запросу «{term}» ничего не нашлось. Попробуйте другое слово, например «рамка».</p>
        )}
      </div>
    </div>
  );
}
