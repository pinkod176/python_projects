import type { MetadataRoute } from "next";
import { getEnv, isDemo } from "@/lib/config/env";

export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  const site = getEnv().SITE_URL;
  if (isDemo()) return { rules: { userAgent: "*", disallow: "/" } };
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/checkout", "/favorites"] },
    sitemap: `${site}/sitemap.xml`,
  };
}
