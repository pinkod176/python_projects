"use client";

import { X } from "lucide-react";
import type { UiParams } from "@/lib/catalog/params";
import type { Facets } from "@/lib/catalog/query";
import { plural } from "@/lib/format";
import { useModalDialog } from "@/components/ui/useModalDialog";
import { Filters } from "./Filters";

type Props = {
  open: boolean;
  onClose: () => void;
  total: number;
  loading: boolean;
  facets: Facets;
  params: UiParams;
  onChange: (patch: Partial<UiParams>) => void;
  onResetAll: () => void;
  dirty: boolean;
};

/** Фильтры на телефоне и планшете: шторка снизу. Изменения применяются сразу, кнопка внизу показывает, сколько работ нашлось. */
export function FilterSheet({ open, onClose, total, loading, facets, params, onChange, onResetAll, dirty }: Props) {
  const dialog = useModalDialog(open, onClose);
  return (
    <dialog {...dialog} aria-label="Фильтры" className="sheet" data-side="bottom">
      <div className="sheet__grip" aria-hidden />
      <div className="flex shrink-0 items-center justify-between px-4 pb-1 pt-2">
        <h2 className="font-display text-[1.75rem]">Фильтры</h2>
        <button type="button" className="icon-btn" aria-label="Закрыть фильтры" onClick={onClose}>
          <X aria-hidden className="size-6" strokeWidth={1.5} />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4">
        <Filters facets={facets} params={params} onChange={onChange} withCategory />
      </div>
      <div className="grid shrink-0 grid-cols-[auto_1fr] gap-2 border-t border-line bg-paper px-4 pt-3 pb-[calc(0.75rem+var(--safe-b))]">
        <button type="button" className="btn btn-ghost" disabled={!dirty} onClick={onResetAll}>
          Сбросить
        </button>
        <button type="button" className="btn btn-solid" onClick={onClose}>
          {loading ? "Обновляем…" : `Показать ${total} ${plural(total, ["работу", "работы", "работ"])}`}
        </button>
      </div>
    </dialog>
  );
}
