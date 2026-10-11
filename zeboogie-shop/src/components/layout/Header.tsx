import Link from "next/link";
import { brand } from "@/content/brand";
import type { Collection } from "@/lib/types";
import { HeaderActions } from "./HeaderActions";
import { HeaderFrame } from "./HeaderFrame";
import { MainNav } from "./MainNav";
import { buildNav } from "./nav";

export function Header({ collections }: { collections: Collection[] }) {
  const { tabs, categories } = buildNav(collections);
  return (
    <HeaderFrame>
      <div className="site-header__bg" aria-hidden />
      <div className="site-header__row container-x">
        <Link href="/" className="site-header__brand">
          <span className="font-display text-[1.75rem] font-medium tracking-[-0.01em] md:text-[2rem]">{brand.name}</span>
          <span className="mt-1 text-[0.62rem] uppercase tracking-[0.24em] text-ink-soft">{brand.descriptor}</span>
          <span className="sr-only"> — на главную</span>
        </Link>
        <MainNav tabs={tabs} categories={categories} />
        <HeaderActions />
      </div>
    </HeaderFrame>
  );
}
