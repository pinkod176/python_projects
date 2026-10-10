import "server-only";

type Level = "info" | "warn" | "error";

const SECRET_KEYS = /token|secret|authorization|password|key/i;

function redact(value: unknown): unknown {
  if (typeof value === "string") {
    return value.replace(/(access_token=)[^&\s]+/gi, "$1***");
  }
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k, SECRET_KEYS.test(k) ? "***" : redact(v)]),
    );
  }
  return value;
}

function write(level: Level, scope: string, message: string, meta?: Record<string, unknown>) {
  const line = JSON.stringify({
    t: new Date().toISOString(),
    level,
    scope,
    message: redact(message),
    ...(meta ? { meta: redact(meta) } : {}),
  });
  (level === "error" ? console.error : level === "warn" ? console.warn : console.log)(line);
}

export const logger = (scope: string) => ({
  info: (m: string, meta?: Record<string, unknown>) => write("info", scope, m, meta),
  warn: (m: string, meta?: Record<string, unknown>) => write("warn", scope, m, meta),
  error: (m: string, meta?: Record<string, unknown>) => write("error", scope, m, meta),
});
