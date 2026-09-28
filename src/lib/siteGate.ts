/** Paths that stay reachable without a site cookie. No secrets live in this module. */
export function isPublicPath(pathname: string): boolean {
  if (pathname === "/login" || pathname === "/api/login") return true;
  if (pathname.startsWith("/_next/static/") || pathname === "/_next/static") return true;
  if (pathname.startsWith("/_next/image")) return true;
  if (pathname === "/favicon.ico" || pathname === "/icon" || pathname === "/icon.svg") return true;
  if (pathname === "/catalyst-logo.webp") return true;
  return false;
}

export function isApiPath(pathname: string): boolean {
  return pathname === "/api" || pathname.startsWith("/api/");
}

/**
 * Only same-site relative paths. Anything else (external URLs, protocol-relative
 * paths, the login page itself) goes back to the map.
 */
export function safeNextPath(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\") || value.includes("\0")) {
    return "/";
  }
  let decoded = value;
  try {
    decoded = decodeURIComponent(value);
  } catch {
    return "/";
  }
  if (!decoded.startsWith("/") || decoded.startsWith("//") || decoded.includes("\\") || decoded.includes("://")) {
    return "/";
  }
  try {
    const url = new URL(value, "https://site.local");
    if (url.origin !== "https://site.local") return "/";
    if (url.pathname === "/login" || url.pathname === "/api/login") return "/";
    return `${url.pathname}${url.search}`;
  } catch {
    return "/";
  }
}
