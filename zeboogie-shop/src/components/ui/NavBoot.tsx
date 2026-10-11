"use client";

import { useEffect } from "react";

/** Запоминает момент перехода «назад/вперёд» (popstate): каталог по нему понимает, что нужно вернуть прокрутку и дозагрузить страницы. */
export function NavBoot() {
  useEffect(() => {
    const onPop = () => {
      window.__zbPop = performance.now();
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  return null;
}
