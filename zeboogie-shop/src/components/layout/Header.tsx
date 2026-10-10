import Link from "next/link";
import { brand } from "@/content/brand";
import type { Collection } from "@/lib/types";
import { HeaderActions } from "./HeaderActions";

export function Header({ collections }: { collections: Collection[] }) {
  const nav = [{ href: "/catalog", label: "Все работы" }, ...collections.map((c) => ({ href: `/catalog?category=${c.id}`, label: c.title })), { href: "/about", label: "О мастерской" }];
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-paper/95 backdrop-blur-sm">
      <div className="container-x flex h-16 items-center justify-between gap-4 md:h-20">
        <Link href="/" className="group flex flex-col leading-none" aria-label={`${brand.name} ${brand.descriptor} — на главную`}>
          <span className="font-serif text-2xl tracking-tight md:text-3xl">{brand.name}</span>
          <span className="mt-1 text-[0.65rem] uppercase tracking-[0.2em] text-ink-soft">{brand.descriptor}</span>
        </Link>
        <nav aria-label="Основная навигация" className="hidden flex-1 justify-center gap-x-7 lg:flex">
          {nav.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="relative py-2 text-[0.95rem] after:absolute after:inset-x-0 after:bottom-0 after:h-px after:origin-left after:scale-x-0 after:bg-ink after:transition-transform hover:after:scale-x-100"
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <HeaderActions nav={nav} />
      </div>
    </header>
  );
}
