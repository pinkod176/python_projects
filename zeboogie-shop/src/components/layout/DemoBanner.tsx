export function DemoBanner() {
  return (
    <div className="border-b border-line bg-paper-2 px-4 py-2 text-center text-xs text-ink-soft">
      <span aria-hidden className="mr-2 inline-block size-1.5 rounded-full bg-copper align-middle" />
      <span className="md:hidden">Демо-режим: данные из выгрузки, не из живого VK</span>
      <span className="hidden md:inline">
        Демонстрационный режим: названия, цены и фото из выгрузки каталога, а не из живого VK. Для реального каталога подключите VK (<code>VK_MODE=live</code>).
      </span>
    </div>
  );
}
