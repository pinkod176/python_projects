/* Ручной/cron-запуск синхронизации: `npm run sync`. Читает .env.local, не требует запущенного сайта. */
import { runSync } from "@/lib/catalog/sync";

runSync().then((r) => {
  console.log(JSON.stringify(r, null, 2));
  process.exit(r.ok ? 0 : 1);
});
