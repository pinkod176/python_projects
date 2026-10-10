/*
 * Скачивает оригиналы фото демо-товаров по ссылкам из src/lib/vk/demo/photo-sources.json
 * в public/demo/products/NN-1.jpg. Запускать там, где доступен CDN ВКонтакте: `npm run demo:photos`.
 * После этого демо-режим сам подставит скачанные фото вместо временных вырезок.
 */
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import sources from "../src/lib/vk/demo/photo-sources.json";

const out = path.resolve(process.cwd(), process.env.PHOTO_OUT_DIR ?? "public/demo/products");
const base = process.env.PHOTO_BASE_URL; // только для проверки скрипта: подмена хоста и папки (PHOTO_OUT_DIR)

async function download(url: string): Promise<Buffer> {
  const res = await fetch(base ? `${base}/${path.basename(new URL(url).pathname)}` : url, {
    signal: AbortSignal.timeout(20_000),
    headers: { "User-Agent": "Mozilla/5.0 (zeboogie demo photo fetch)" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  if (!(res.headers.get("content-type") ?? "").startsWith("image/")) throw new Error("не изображение");
  return Buffer.from(await res.arrayBuffer());
}

async function main() {
  await mkdir(out, { recursive: true });
  let ok = 0;
  const failed: string[] = [];
  for (const [nn, url] of Object.entries(sources as Record<string, string>)) {
    try {
      await writeFile(path.join(out, `${nn}-1.jpg`), await download(url));
      ok++;
    } catch (e) {
      failed.push(`${nn}: ${e instanceof Error ? e.message : e}`);
    }
  }
  console.log(`Скачано: ${ok} из ${Object.keys(sources).length}`);
  if (failed.length) console.log("Не удалось:\n  " + failed.join("\n  "));
  process.exit(failed.length ? 1 : 0);
}
void main();
