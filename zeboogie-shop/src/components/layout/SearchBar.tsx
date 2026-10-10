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
    <div className={`relative ${className}`}>
      <form onSubmit={submit} role="search" className="flex items-center border-b border-ink/50 focus-within:border-ink">
        <Search aria-hidden className="size-5 shrink-0 text-ink-soft" strokeWidth={1.5} />
        <label htmlFor={`${listId}-input`} className="sr-only">Поиск по каталогу</label>
        <input
          id={`${listId}-input`}
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoFocus={autoFocus}
          placeholder="Найти рамку, брошь, арт-объект…"
          autoComplete="off"
          enterKeyHint="search"
          className="min-h-12 w-full bg-transparent px-3 text-base outline-none placeholder:text-ink-soft"
        />
        <button type="submit" className="min-h-12 px-3 text-sm font-medium hover:text-moss">Найти</button>
      </form>
      {show.length > 0 && (
        <ul id={listId} className="absolute inset-x-0 top-full z-10 mt-1 border border-line bg-paper shadow-sm">
          {show.map((p) => (
            <li key={p.vkId}>
              <Link
                href={`/product/${p.slug}`}
                onClick={onNavigate}
                className="flex min-h-12 items-center justify-between gap-4 px-4 py-2 hover:bg-paper-2"
              >
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
