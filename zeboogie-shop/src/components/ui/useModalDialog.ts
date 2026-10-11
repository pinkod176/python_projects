"use client";

import { useEffect, useRef, type MouseEvent, type PointerEvent } from "react";

/**
 * Связывает состояние React с нативным <dialog>: showModal() даёт фокус-ловушку, Esc и «верхний слой»
 * (поэтому на телефоне окно не зависит от transform/z-index родителей). Закрытие нативным способом (Esc, форма)
 * сообщается наружу через onClose. Клик по подложке (сам <dialog>, у которого нет отступов) тоже закрывает окно —
 * но только если и нажатие, и отпускание были на подложке: выделение текста, закончившееся за краем окна, его не закрывает.
 */
export function useModalDialog(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null);
  const downOnBackdrop = useRef(false);

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
    onPointerDown: (e: PointerEvent<HTMLDialogElement>) => {
      downOnBackdrop.current = e.target === ref.current;
    },
    onClick: (e: MouseEvent<HTMLDialogElement>) => {
      const closing = downOnBackdrop.current && e.target === ref.current;
      downOnBackdrop.current = false;
      if (closing) onClose();
    },
  };
}
