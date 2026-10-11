export function DemoBanner() {
  return (
    <div className="demo-banner">
      <span aria-hidden className="mr-2 inline-block size-1.5 shrink-0 rounded-full bg-copper" />
      <span className="md:hidden">Демо: данные из выгрузки, не из живого VK</span>
      <span className="hidden md:inline">
        Демонстрационный режим: названия, цены и фото из выгрузки каталога, а не из живого VK. Для реального каталога подключите VK (<code>VK_MODE=live</code>).
      </span>
    </div>
  );
}
