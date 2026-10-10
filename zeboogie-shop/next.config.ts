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

const nextConfig: NextConfig = {
  poweredByHeader: false,
  images: {
    remotePatterns: VK_IMAGE_HOSTS.map((hostname) => ({ protocol: "https", hostname })),
    formats: ["image/avif", "image/webp"],
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
