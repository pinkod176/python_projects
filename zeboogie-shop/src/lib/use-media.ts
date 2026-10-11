"use client";

import { useSyncExternalStore } from "react";

/** Совпадает ли медиа-запрос (на сервере и при гидрации — `fallback`, затем реальное значение без «мигания» разметки). */
export function useMedia(query: string, fallback = false): boolean {
  return useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia(query);
      mq.addEventListener("change", cb);
      return () => mq.removeEventListener("change", cb);
    },
    () => window.matchMedia(query).matches,
    () => fallback,
  );
}
