import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "@/app/api/login/route";
import { middleware } from "@/middleware";
import { isApiPath, isPublicPath, safeNextPath } from "@/lib/siteGate";
import {
  SITE_AUTH_COOKIE,
  SITE_AUTH_MAX_AGE_SECONDS,
  cookieAuthorizes,
  loginToken,
  readSitePassword,
  siteAuthToken,
  timingSafeEqualString,
} from "@/lib/siteAuth";

const PASSWORD = "test-gate-password";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("site password gate", () => {
  it("derives a stable HMAC that is not the password and changes with the password", async () => {
    const token = await siteAuthToken(PASSWORD);
    expect(token).toMatch(/^[0-9a-f]{64}$/);
    expect(token).not.toContain(PASSWORD);
    expect(token).not.toBe(PASSWORD);
    expect(await siteAuthToken(PASSWORD)).toBe(token);
    expect(await siteAuthToken(`${PASSWORD}-rotated`)).not.toBe(token);
  });

  it("compares with constant-time equality", () => {
    expect(timingSafeEqualString("abc", "abc")).toBe(true);
    expect(timingSafeEqualString("abc", "abd")).toBe(false);
    expect(timingSafeEqualString("abc", "abcd")).toBe(false);
    expect(timingSafeEqualString("", "")).toBe(true);
    expect(timingSafeEqualString("a", "")).toBe(false);
  });

  it("fails closed when SITE_PASSWORD is unset or empty", async () => {
    vi.stubEnv("SITE_PASSWORD", "");
    expect(readSitePassword()).toBeNull();
    expect(await loginToken(PASSWORD, readSitePassword())).toBeNull();
    expect(await cookieAuthorizes(await siteAuthToken(PASSWORD), null)).toBe(false);

    vi.stubEnv("SITE_PASSWORD", undefined);
    delete process.env.SITE_PASSWORD;
    expect(readSitePassword()).toBeNull();
  });

  it("accepts only the configured password and the matching cookie", async () => {
    const token = await loginToken(PASSWORD, PASSWORD);
    expect(token).toBe(await siteAuthToken(PASSWORD));
    expect(await loginToken("nope", PASSWORD)).toBeNull();
    expect(await cookieAuthorizes(token ?? undefined, PASSWORD)).toBe(true);
    expect(await cookieAuthorizes(PASSWORD, PASSWORD)).toBe(false);
    expect(await cookieAuthorizes(await siteAuthToken("other"), PASSWORD)).toBe(false);
  });

  it("keeps the login page, login API, and login assets public", () => {
    expect(isPublicPath("/login")).toBe(true);
    expect(isPublicPath("/api/login")).toBe(true);
    expect(isPublicPath("/_next/static/chunks/main.js")).toBe(true);
    expect(isPublicPath("/_next/image")).toBe(true);
    expect(isPublicPath("/favicon.ico")).toBe(true);
    expect(isPublicPath("/icon.svg")).toBe(true);
    expect(isPublicPath("/catalyst-logo.webp")).toBe(true);
    expect(isPublicPath("/")).toBe(false);
    expect(isPublicPath("/api/parcels")).toBe(false);
    expect(isPublicPath("/api/geocode")).toBe(false);
    expect(isPublicPath("/api/parcel-coverage")).toBe(false);
    expect(isApiPath("/api/parcels")).toBe(true);
    expect(isApiPath("/login")).toBe(false);
  });

  it("only allows a same-site next path", () => {
    expect(safeNextPath("/")).toBe("/");
    expect(safeNextPath("/?market=Orlando")).toBe("/?market=Orlando");
    expect(safeNextPath("https://evil.example/phish")).toBe("/");
    expect(safeNextPath("//evil.example")).toBe("/");
    expect(safeNextPath("/\\evil.example")).toBe("/");
    expect(safeNextPath("/%2F%2Fevil.example")).toBe("/");
    expect(safeNextPath("/login")).toBe("/");
    expect(safeNextPath(null)).toBe("/");
  });
});

describe("middleware", () => {
  it("redirects pages and rejects APIs when the password is unset", async () => {
    vi.stubEnv("SITE_PASSWORD", "");
    const page = await middleware(new NextRequest("http://localhost:3000/markets?x=1"));
    expect(page.status).toBe(307);
    expect(page.headers.get("location")).toBe("http://localhost:3000/login?next=%2Fmarkets%3Fx%3D1");

    const api = await middleware(new NextRequest("http://localhost:3000/api/parcels"));
    expect(api.status).toBe(401);
    expect(await api.json()).toEqual({ error: "Unauthorized" });

    const login = await middleware(new NextRequest("http://localhost:3000/login"));
    expect(login.status).toBe(200);
    expect(login.headers.get("location")).toBeNull();
  });

  it("lets a valid cookie through and ignores a stale cookie", async () => {
    vi.stubEnv("SITE_PASSWORD", PASSWORD);
    const token = await siteAuthToken(PASSWORD);
    const allowed = await middleware(
      new NextRequest("http://localhost:3000/api/geocode?q=28.5,-81.3", {
        headers: { cookie: `${SITE_AUTH_COOKIE}=${token}` },
      }),
    );
    expect(allowed.status).toBe(200);
    expect(allowed.headers.get("x-middleware-next")).toBe("1");

    const stale = await siteAuthToken("previous-password");
    const denied = await middleware(
      new NextRequest("http://localhost:3000/", {
        headers: { cookie: `${SITE_AUTH_COOKIE}=${stale}` },
      }),
    );
    expect(denied.status).toBe(307);
    expect(denied.headers.get("location")).toContain("/login?next=%2F");
  });
});

describe("login API", () => {
  it("sets an httpOnly Secure SameSite=Lax cookie for 30 days and does not store the password", async () => {
    vi.stubEnv("SITE_PASSWORD", PASSWORD);
    const response = await POST(
      new Request("http://localhost:3000/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: PASSWORD }),
      }),
    );
    expect(response.status).toBe(200);
    const setCookie = response.headers.get("set-cookie") ?? "";
    const token = await siteAuthToken(PASSWORD);
    expect(setCookie).toContain(`${SITE_AUTH_COOKIE}=${token}`);
    expect(setCookie).not.toContain(PASSWORD);
    expect(setCookie).toMatch(/HttpOnly/i);
    expect(setCookie).toMatch(/Secure/i);
    expect(setCookie).toMatch(/SameSite=Lax/i);
    expect(setCookie).toContain(`Max-Age=${SITE_AUTH_MAX_AGE_SECONDS}`);
    expect(SITE_AUTH_MAX_AGE_SECONDS).toBe(60 * 60 * 24 * 30);
  });

  it("returns Incorrect password for a wrong password and when the env var is unset", async () => {
    vi.stubEnv("SITE_PASSWORD", PASSWORD);
    const wrong = await POST(
      new Request("http://localhost:3000/api/login", {
        method: "POST",
        body: JSON.stringify({ password: "wrong" }),
      }),
    );
    expect(wrong.status).toBe(401);
    expect(await wrong.json()).toEqual({ error: "Incorrect password" });
    expect(wrong.headers.get("set-cookie")).toBeNull();

    vi.stubEnv("SITE_PASSWORD", "");
    const closed = await POST(
      new Request("http://localhost:3000/api/login", {
        method: "POST",
        body: JSON.stringify({ password: PASSWORD }),
      }),
    );
    expect(closed.status).toBe(401);
    expect(await closed.json()).toEqual({ error: "Incorrect password" });
  });
});

describe("same-origin API fetches", () => {
  it("does not drop cookies on the app's own /api fetches", () => {
    const files = sourceFiles(path.join(process.cwd(), "src")).filter((file) => file.endsWith(".ts") || file.endsWith(".tsx"));
    const offenders: string[] = [];
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      if (!source.includes("/api/")) continue;
      if (/credentials\s*:\s*["']omit["']/.test(source)) offenders.push(file);
    }
    expect(offenders).toEqual([]);

    const shell = readFileSync(path.join(process.cwd(), "src/components/AppShell.tsx"), "utf8");
    const map = readFileSync(path.join(process.cwd(), "src/components/SiteMap.tsx"), "utf8");
    expect(shell).toContain("fetch(`/api/parcels?");
    expect(shell).toContain("fetch(`/api/geocode?");
    expect(shell).toContain("fetch(`/api/screening/point?");
    expect(map).toContain('fetch("/api/parcel-coverage")');
    expect(shell).not.toMatch(/credentials\s*:/);
    expect(map).not.toMatch(/credentials\s*:/);

    const login = readFileSync(path.join(process.cwd(), "src/components/LoginForm.tsx"), "utf8");
    expect(login).toContain('credentials: "same-origin"');
    expect(login).not.toContain("siteAuth");
    expect(readFileSync(path.join(process.cwd(), "src/lib/siteGate.ts"), "utf8")).not.toContain("SITE_PASSWORD");
  });

  it("shows the logo, a password field, and an Enter button", () => {
    const page = readFileSync(path.join(process.cwd(), "src/app/login/page.tsx"), "utf8");
    const form = readFileSync(path.join(process.cwd(), "src/components/LoginForm.tsx"), "utf8");
    expect(page).toContain("<CompanyLogo");
    expect(form).toContain('type="password"');
    expect(form).toContain("Incorrect password");
    expect(form).toMatch(/>\s*Enter\s*</);
  });
});

function sourceFiles(dir: string): string[] {
  const entries = readdirSync(dir);
  const files: string[] = [];
  for (const entry of entries) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) files.push(...sourceFiles(full));
    else files.push(full);
  }
  return files;
}
