"use client";

import { useSyncExternalStore } from "react";

/** Небольшие настройки интерфейса в localStorage (вид сетки, свёрнутая панель фильтров). Сервер всегда отдаёт значение по умолчанию. */
const listeners = new Set<() => void>();

export function setPref(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* хранилище недоступно — настройка живёт до перезагрузки */
    memory.set(key, value);
  }
  listeners.forEach((l) => l());
}

const memory = new Map<string, string>();

function read(key: string, fallback: string): string {
  try {
    return window.localStorage.getItem(key) ?? memory.get(key) ?? fallback;
  } catch {
    return memory.get(key) ?? fallback;
  }
}

export function usePref(key: string, fallback: string): string {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      const onStorage = (e: StorageEvent) => e.key === key && cb();
      window.addEventListener("storage", onStorage);
      return () => {
        listeners.delete(cb);
        window.removeEventListener("storage", onStorage);
      };
    },
    () => read(key, fallback),
    () => fallback,
  );
}
