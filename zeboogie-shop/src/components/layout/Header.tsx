import Link from "next/link";
import { brand } from "@/content/brand";
import type { Collection } from "@/lib/types";
import { HeaderActions } from "./HeaderActions";
import { HeaderFrame } from "./HeaderFrame";

export function Header({ collections }: { collections: Collection[] }) {
  const nav = [
    { href: "/catalog", label: "Все работы" },
    ...collections.map((c) => ({ href: `/catalog?category=${c.id}`, label: c.title })),
    { href: "/about", label: "О мастерской" },
  ];
  return (
    <HeaderFrame>
      <div className="site-header__bg" aria-hidden />
      <div className="site-header__row container-x">
        <Link href="/" className="site-header__brand flex flex-col leading-none">
          <span className="font-display text-[1.75rem] font-medium tracking-[-0.01em] md:text-[2rem]">{brand.name}</span>
          <span className="mt-1 text-[0.62rem] uppercase tracking-[0.24em] text-ink-soft">{brand.descriptor}</span>
          <span className="sr-only"> — на главную</span>
        </Link>
        <nav aria-label="Основная навигация" className="hidden flex-1 justify-center gap-x-8 xl:flex">
          {nav.map((n) => (
            <Link key={n.href} href={n.href} className="u-link py-2 text-[0.95rem]">
              {n.label}
            </Link>
          ))}
        </nav>
        <HeaderActions nav={nav} />
      </div>
    </HeaderFrame>
  );
}
