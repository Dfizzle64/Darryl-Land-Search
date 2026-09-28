/** httpOnly session cookie. The value is an HMAC, never SITE_PASSWORD. */
export const SITE_AUTH_COOKIE = "site_auth";

/** 30 days. Changing SITE_PASSWORD changes the HMAC, so old cookies stop matching. */
export const SITE_AUTH_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

export function siteAuthCookieOptions() {
  return {
    httpOnly: true as const,
    secure: true as const,
    sameSite: "lax" as const,
    path: "/",
    maxAge: SITE_AUTH_MAX_AGE_SECONDS,
  };
}

function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith("/")) return pathname.slice(0, -1);
  return pathname;
}

/** Login page, login API, and the static files that page needs. */
export function isPublicPath(pathname: string): boolean {
  const path = normalizePath(pathname);
  if (path === "/login" || path === "/api/login") return true;
  if (path.startsWith("/_next/static") || path.startsWith("/_next/image") || path === "/_next/webpack-hmr") {
    return true;
  }
  if (path === "/favicon.ico" || path === "/icon" || path === "/icon.svg" || path === "/catalyst-logo.webp") {
    return true;
  }
  return false;
}

export function isApiPath(pathname: string): boolean {
  const path = normalizePath(pathname);
  return path === "/api" || path.startsWith("/api/");
}

/**
 * Only same-origin paths. Rejects protocol-relative and absolute URLs so
 * `next` cannot be used as an open redirect.
 */
export function safeNextPath(value: string | null | undefined): string {
  if (typeof value !== "string" || value.length === 0 || value.length > 2048) return "/";
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\") || value.includes("://")) {
    return "/";
  }
  let url: URL;
  try {
    url = new URL(value, "https://gate.local");
  } catch {
    return "/";
  }
  if (url.origin !== "https://gate.local") return "/";
  if (!url.pathname.startsWith("/") || url.pathname.startsWith("//")) return "/";
  const path = normalizePath(url.pathname);
  if (path === "/login") return "/";
  return `${path}${url.search}`;
}

export type GateResult = { action: "allow" } | { action: "unauthorized" } | { action: "redirect"; next: string };

export function redirectNext(pathname: string, search: string): string {
  const normalizedSearch = search && !search.startsWith("?") ? `?${search}` : search;
  return `${normalizePath(pathname) || "/"}${normalizedSearch}`;
}
