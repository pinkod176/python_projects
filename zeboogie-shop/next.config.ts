import type { NextConfig } from "next";

// Хосты CDN ВКонтакте, с которых приходят фотографии товаров.
const VK_IMAGE_HOSTS = [
  "**.userapi.com",
  "**.vkuser.net",
  "**.vk.com",
  "**.vk.ru",
  "**.mycdn.me",
  "**.okcdn.ru",
];

/**
 * Открываете `npm run dev` с телефона по адресу вида http://192.168.1.50:3000? Next 16 в режиме разработки
 * блокирует «dev-ресурсы» (в том числе WebSocket горячей перезагрузки) для любого хоста, кроме localhost.
 * Без этого списка страница рисуется, но React не запускается — и ВСЕ кнопки на телефоне «мёртвые».
 * Здесь разрешены частные сети (домашний Wi-Fi) и имена *.local. Свой хост/туннель добавьте через
 * переменную DEV_ALLOWED_ORIGINS=host1,*.tunnel.example.com. На production-сборку (npm start) это не влияет.
 */
const allowedDevOrigins = [
  "192.168.*.*",
  "10.*.*.*",
  ...Array.from({ length: 16 }, (_, i) => `172.${16 + i}.*.*`),
  "*.local",
  ...(process.env.DEV_ALLOWED_ORIGINS?.split(",").map((h) => h.trim()).filter(Boolean) ?? []),
];

const nextConfig: NextConfig = {
  allowedDevOrigins,
  // Плавающий значок «N» режима разработки сидит в левом нижнем углу и на телефоне перекрывает нижнюю панель:
  // тапы по её крайней кнопке уходили в него (ещё одна причина «мёртвых» кнопок в `npm run dev`). Ошибки Next по-прежнему показывает.
  devIndicators: false,
  poweredByHeader: false,
  // CSS встраивается в HTML: нет отдельного блокирующего запроса, шрифты находятся раньше.
  experimental: { inlineCss: true },
  images: {
    remotePatterns: VK_IMAGE_HOSTS.map((hostname) => ({ protocol: "https", hostname })),
    // AVIF/WebP отдаются браузерам, которые их понимают; остальные получают JPEG из исходника.
    formats: ["image/avif", "image/webp"],
    // 75 — карточки, 82 — крупные фото (hero, страница товара). Других значений next/image не принимает.
    qualities: [75, 82],
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
        ],
      },
    ];
  },
};

export default nextConfig;
