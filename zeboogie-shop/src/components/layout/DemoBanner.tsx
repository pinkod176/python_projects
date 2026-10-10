export function DemoBanner() {
  return (
    <div className="bg-wood px-4 py-2 text-center text-xs text-paper">
      Демонстрационный режим: названия, цены и фото из выгрузки каталога, а не из живого VK.
      Для реального каталога подключите VK (<code>VK_MODE=live</code>).
    </div>
  );
}
