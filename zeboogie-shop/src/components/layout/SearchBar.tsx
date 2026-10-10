"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { formatMoney } from "@/lib/format";
import type { CatalogResult } from "@/lib/catalog/query";

type Props = { autoFocus?: boolean; onNavigate?: () => void; className?: string };

/** Поиск с подсказками. Подсказки берутся из внутреннего API каталога, не из VK. */
export function SearchBar({ autoFocus, onNavigate, className = "" }: Props) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [hints, setHints] = useState<CatalogResult["items"]>([]);
  const listId = useId();
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) return;
    const t = setTimeout(async () => {
      abort.current?.abort();
      abort.current = new AbortController();
      try {
        const res = await fetch(`/api/catalog?q=${encodeURIComponent(term)}&pageSize=5`, { signal: abort.current.signal });
        if (res.ok) setHints(((await res.json()) as CatalogResult).items);
      } catch {
        /* запрос отменён или сеть недоступна — подсказки просто не показываем */
      }
    }, 200);
    return () => clearTimeout(t);
  }, [q]);

  const show = q.trim().length >= 2 ? hints : [];

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const term = q.trim();
    router.push(term ? `/catalog?q=${encodeURIComponent(term)}` : "/catalog");
    onNavigate?.();
  }

  return (
    <div className={className}>
      <form onSubmit={submit} role="search" className="flex items-stretch gap-2">
        <div className="relative flex-1">
          <Search aria-hidden className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-ink-soft" strokeWidth={1.5} />
          <label htmlFor={`${listId}-input`} className="sr-only">Поиск по каталогу</label>
          <input
            id={`${listId}-input`}
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            autoFocus={autoFocus}
            placeholder="Рамка, брошь, арт-объект…"
            autoComplete="off"
            enterKeyHint="search"
            className="field pl-12"
          />
        </div>
        <button type="submit" className="btn btn-solid !px-5">Найти</button>
      </form>
      {show.length > 0 && (
        <ul id={listId} className="mt-3 divide-y divide-line border-t border-line">
          {show.map((p) => (
            <li key={p.vkId}>
              <Link href={`/product/${p.slug}`} onClick={onNavigate} className="flex min-h-12 items-center justify-between gap-4 py-2 transition-colors hover:text-wood">
                <span className="truncate">{p.title}</span>
                {p.price && <span className="shrink-0 text-sm text-ink-soft">{formatMoney(p.price)}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
