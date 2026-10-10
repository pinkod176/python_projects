import "server-only";
import { getEnv } from "@/lib/config/env";
import { logger } from "@/lib/log";
import { VkApiError, explainCode, isRetryableCode } from "./errors";

const log = logger("vk");

/** Минимальный интервал между запросами: лимит VK — 3 запроса/с для пользовательских и сервисных ключей. */
const MIN_INTERVAL_MS = 350;
const MAX_ATTEMPTS = 5;
const REQUEST_TIMEOUT_MS = 15_000;

let lastRequestAt = 0;
let queue: Promise<unknown> = Promise.resolve();

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Сериализует запросы и выдерживает интервал, чтобы не упираться в лимиты. */
function throttle<T>(fn: () => Promise<T>): Promise<T> {
  const run = queue.then(async () => {
    const wait = lastRequestAt + MIN_INTERVAL_MS - Date.now();
    if (wait > 0) await sleep(wait);
    lastRequestAt = Date.now();
    return fn();
  });
  queue = run.catch(() => undefined);
  return run;
}

type Params = Record<string, string | number | boolean | undefined>;

/**
 * Единственная точка обращения к VK API. Токен добавляется только здесь, на сервере,
 * и никогда не попадает в логи, ошибки или ответы клиенту.
 */
export async function vkCall(method: string, params: Params = {}): Promise<unknown> {
  const env = getEnv();
  if (!env.VK_ACCESS_TOKEN) {
    throw new VkApiError("VK_ACCESS_TOKEN не задан: добавьте токен в .env.local или переключитесь на VK_MODE=demo.", null, false);
  }
  const body = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined) body.set(k, String(v));
  body.set("v", env.VK_API_VERSION);
  body.set("lang", "ru");

  let lastError: unknown;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    try {
      const data = await throttle(async () => {
        const res = await fetch(`${env.VK_API_BASE}/${method}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: `Bearer ${env.VK_ACCESS_TOKEN}`,
          },
          body,
          cache: "no-store",
          signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        });
        if (!res.ok) throw new VkApiError(`VK API ответил HTTP ${res.status}`, null, res.status >= 500 || res.status === 429);
        return (await res.json()) as { response?: unknown; error?: { error_code: number; error_msg: string } };
      });

      if (data.error) {
        const { error_code: code, error_msg: msg } = data.error;
        throw new VkApiError(`${method}: [${code}] ${msg}. ${explainCode(code)}`, code, isRetryableCode(code));
      }
      if (data.response === undefined) throw new VkApiError(`${method}: пустой ответ`, null, true);
      return data.response;
    } catch (e) {
      lastError = e;
      const retryable =
        e instanceof VkApiError ? e.retryable : e instanceof Error && (e.name === "TimeoutError" || e.name === "TypeError");
      if (!retryable || attempt === MAX_ATTEMPTS) break;
      const delay = Math.min(8000, 500 * 2 ** (attempt - 1));
      log.warn(`${method}: попытка ${attempt} не удалась, повтор через ${delay} мс`, {
        reason: e instanceof Error ? e.message : String(e),
      });
      await sleep(delay);
    }
  }
  if (lastError instanceof VkApiError) throw lastError;
  throw new VkApiError(`${method}: сеть недоступна (${lastError instanceof Error ? lastError.message : "неизвестная ошибка"})`, null, true);
}
