"use client";

import { useEffect, useRef, type MouseEvent } from "react";

/**
 * Связывает состояние React с нативным <dialog>: showModal() даёт фокус-ловушку, Esc и «верхний слой»
 * (поэтому на телефоне окно не зависит от transform/z-index родителей). Закрытие нативным способом (Esc, форма)
 * сообщается наружу через onClose. Клик по подложке (сам <dialog>, у которого нет отступов) тоже закрывает окно.
 */
export function useModalDialog(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      d.showModal();
      // showModal() ставит фокус на первый элемент окна (кнопку «Закрыть»); поле поиска и т. п. помечаем data-autofocus.
      d.querySelector<HTMLElement>("[data-autofocus]")?.focus({ preventScroll: true });
    }
    if (!open && d.open) d.close();
  }, [open]);

  return {
    ref,
    onClose,
    onClick: (e: MouseEvent<HTMLDialogElement>) => {
      if (e.target === ref.current) onClose();
    },
  };
}
