import { ViewTransition, type ReactNode } from "react";

/**
 * Мягкий переход между страницами.
 * template.tsx пересоздаётся при каждой навигации, поэтому <ViewTransition> получает enter/exit:
 *  - в браузерах с View Transitions API старая страница плавно гаснет, новая проявляется (см. globals.css, .page-out / .page-in);
 *  - в остальных работает CSS-фолбэк .page-enter (простой fade, только если API не поддерживается).
 */
export default function Template({ children }: { children: ReactNode }) {
  return (
    <ViewTransition enter="page-in" exit="page-out" default="none">
      <div className="page-enter">{children}</div>
    </ViewTransition>
  );
}
