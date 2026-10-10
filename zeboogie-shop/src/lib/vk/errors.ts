/** Ошибки модуля VK. Коды — https://dev.vk.com/ru/reference/errors */
export class VkApiError extends Error {
  constructor(
    message: string,
    readonly code: number | null,
    readonly retryable: boolean,
  ) {
    super(message);
    this.name = "VkApiError";
  }
}

/** 1 — неизвестная ошибка, 6 — слишком много запросов/с, 9 — флуд-контроль, 10 — внутренняя ошибка. */
const RETRYABLE = new Set([1, 6, 9, 10]);

export function isRetryableCode(code: number | undefined): boolean {
  return code !== undefined && RETRYABLE.has(code);
}

export function explainCode(code: number | undefined): string {
  switch (code) {
    case 5:
      return "Токен недействителен или не имеет нужных прав (ошибка авторизации).";
    case 15:
      return "Доступ запрещён: проверьте, что у токена есть доступ к товарам сообщества.";
    case 27:
    case 28:
      return "Токен не подходит для этого метода.";
    case 100:
      return "Некорректный параметр запроса (проверьте VK_GROUP).";
    case 203:
      return "Нет доступа к сообществу.";
    case 6:
    case 9:
      return "Превышен лимит запросов VK API.";
    default:
      return "Ошибка VK API.";
  }
}
