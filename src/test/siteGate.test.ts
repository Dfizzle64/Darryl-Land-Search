import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "../app/api/login/route";
import { middleware } from "../middleware";
import {
  PASSWORD_HASH,
  PASSWORD_SALT,
  expectedPasswordHash,
  gateRequest,
  optionalSitePassword,
  passwordDigest,
  sessionToken,
  tokensMatch,
} from "../lib/siteAuth";
import {
  SITE_AUTH_COOKIE,
  SITE_AUTH_MAX_AGE_SECONDS,
  isPublicPath,
  safeNextPath,
  siteAuthCookieOptions,
} from "../lib/siteGate";

const ORIGINAL = process.env.SITE_PASSWORD;

afterEach(() => {
  if (ORIGINAL === undefined) delete process.env.SITE_PASSWORD;
  else process.env.SITE_PASSWORD = ORIGINAL;
});

describe("site password token", () => {
  it("stores a salted sha256 and a distinct HMAC cookie", () => {
    delete process.env.SITE_PASSWORD;
    expect(PASSWORD_SALT.endsWith(":")).toBe(true);
    expect(PASSWORD_HASH).toMatch(/^[0-9a-f]{64}$/);
    expect(expectedPasswordHash()).toBe(PASSWORD_HASH);
    const token = sessionToken(PASSWORD_HASH);
    expect(token).toMatch(/^[0-9a-f]{64}$/);
    expect(token).not.toBe(PASSWORD_HASH);
    expect(sessionToken(passwordDigest("other-secret"))).not.toBe(token);
  });

  it("compares hashes in constant time and rejects length mismatches", () => {
    const hash = passwordDigest("correct-horse");
    expect(tokensMatch(hash, hash)).toBe(true);
    expect(tokensMatch(passwordDigest("other-horse"), hash)).toBe(false);
    expect(tokensMatch("short", hash)).toBe(false);
    expect(tokensMatch("correct-horse", hash)).toBe(false);
  });

  it("uses the built-in hash when SITE_PASSWORD is unset and lets it override", () => {
    delete process.env.SITE_PASSWORD;
    expect(optionalSitePassword()).toBeNull();
    expect(expectedPasswordHash()).toBe(PASSWORD_HASH);
    process.env.SITE_PASSWORD = "";
    expect(optionalSitePassword()).toBeNull();
    expect(expectedPasswordHash()).toBe(PASSWORD_HASH);
    process.env.SITE_PASSWORD = "correct-horse";
    expect(expectedPasswordHash()).toBe(passwordDigest("correct-horse"));
    expect(expectedPasswordHash()).not.toBe(PASSWORD_HASH);
  });

  it("sets an httpOnly Secure SameSite=Lax cookie for 30 days", () => {
    expect(siteAuthCookieOptions()).toEqual({
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 30,
    });
    expect(SITE_AUTH_MAX_AGE_SECONDS).toBe(2592000);
  });
});

describe("gate", () => {
  it("allows the login page, login API, and login assets without a cookie", () => {
    delete process.env.SITE_PASSWORD;
    for (const pathname of [
      "/login",
      "/api/login",
      "/_next/static/chunks/app.js",
      "/_next/image",
      "/favicon.ico",
      "/icon.svg",
      "/icon",
      "/catalyst-logo.webp",
    ]) {
      expect(isPublicPath(pathname)).toBe(true);
      expect(gateRequest({ pathname, search: "", cookie: undefined }).action).toBe("allow");
    }
  });

  it("accepts the built-in hash cookie when SITE_PASSWORD is unset", () => {
    delete process.env.SITE_PASSWORD;
    const cookie = sessionToken(PASSWORD_HASH);
    expect(gateRequest({ pathname: "/", search: "", cookie }).action).toBe("allow");
    expect(gateRequest({ pathname: "/api/parcels", search: "?minAcres=5", cookie }).action).toBe("allow");
  });

  it("redirects pages and rejects API routes until the cookie matches", () => {
    delete process.env.SITE_PASSWORD;
    expect(gateRequest({ pathname: "/", search: "?market=Orlando", cookie: undefined })).toEqual({
      action: "redirect",
      next: "/?market=Orlando",
    });
    expect(gateRequest({ pathname: "/api/geocode", search: "?q=orlando", cookie: "nope" }).action).toBe("unauthorized");
    expect(gateRequest({ pathname: "/api/parcels/abc", search: "", cookie: sessionToken(PASSWORD_HASH) }).action).toBe(
      "allow",
    );
  });

  it("invalidates cookies when SITE_PASSWORD overrides the built-in hash", () => {
    delete process.env.SITE_PASSWORD;
    const builtIn = sessionToken(PASSWORD_HASH);
    process.env.SITE_PASSWORD = "new-password";
    expect(gateRequest({ pathname: "/api/parcel-coverage", search: "", cookie: builtIn }).action).toBe("unauthorized");
    expect(
      gateRequest({ pathname: "/", search: "", cookie: sessionToken(passwordDigest("new-password")) }).action,
    ).toBe("allow");
  });

  it("keeps next on this site", () => {
    expect(safeNextPath("/?market=Orlando")).toBe("/?market=Orlando");
    expect(safeNextPath("/api/parcels?minAcres=5")).toBe("/api/parcels?minAcres=5");
    expect(safeNextPath("https://evil.example/phish")).toBe("/");
    expect(safeNextPath("//evil.example")).toBe("/");
    expect(safeNextPath("/\\evil.example")).toBe("/");
    expect(safeNextPath("/login?next=/")).toBe("/");
    expect(safeNextPath(null)).toBe("/");
  });
});

describe("login API", () => {
  it("sets an HMAC cookie for the override password", async () => {
    process.env.SITE_PASSWORD = "correct-horse";
    const hash = passwordDigest("correct-horse");
    const response = await POST(
      new Request("http://localhost/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: "correct-horse" }),
      }),
    );
    expect(response.status).toBe(200);
    const setCookie = response.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain(`${SITE_AUTH_COOKIE}=${sessionToken(hash)}`);
    expect(setCookie).not.toContain("correct-horse");
    expect(setCookie).not.toContain(hash);
    expect(setCookie.toLowerCase()).toContain("httponly");
    expect(setCookie.toLowerCase()).toContain("secure");
    expect(setCookie.toLowerCase()).toContain("samesite=lax");
    expect(setCookie).toContain("Max-Age=2592000");
  });

  it("returns Incorrect password for a wrong password", async () => {
    delete process.env.SITE_PASSWORD;
    const wrong = await POST(
      new Request("http://localhost/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: "nope" }),
      }),
    );
    expect(wrong.status).toBe(401);
    expect(await wrong.json()).toEqual({ error: "Incorrect password" });
    expect(wrong.headers.get("set-cookie")).toBeNull();
  });
});

describe("middleware", () => {
  it("redirects pages to /login and returns 401 for API routes", () => {
    delete process.env.SITE_PASSWORD;
    const page = middleware(new NextRequest("http://localhost:3000/?market=Orlando"));
    expect(page.status).toBe(307);
    const location = page.headers.get("location") ?? "";
    const next = new URL(location).searchParams.get("next");
    expect(new URL(location).pathname).toBe("/login");
    expect(next).toBe("/?market=Orlando");

    const api = middleware(new NextRequest("http://localhost:3000/api/parcels?minAcres=5"));
    expect(api.status).toBe(401);

    const login = middleware(new NextRequest("http://localhost:3000/login?next=%2F"));
    expect(login.status).toBe(200);
  });

  it("allows a matching cookie through to API routes", () => {
    delete process.env.SITE_PASSWORD;
    const request = new NextRequest("http://localhost:3000/api/geocode?q=orlando", {
      headers: { cookie: `${SITE_AUTH_COOKIE}=${sessionToken(PASSWORD_HASH)}` },
    });
    expect(middleware(request).status).toBe(200);
  });
});

function walk(dir: string): string[] {
  const entries = readdirSync(dir);
  const files: string[] = [];
  for (const entry of entries) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) files.push(...walk(full));
    else files.push(full);
  }
  return files;
}

describe("same-origin API fetches", () => {
  it("does not omit cookies on the app's own /api fetches", () => {
    const root = path.join(process.cwd(), "src");
    const files = walk(root).filter(
      (file) => /\.(ts|tsx)$/.test(file) && !file.includes(`${path.sep}app${path.sep}api${path.sep}`) && !file.endsWith(".test.ts"),
    );
    const calls: string[] = [];
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      const pattern = /fetch\(\s*(["'`])\/api\/[\s\S]*?\1[\s\S]*?\)/g;
      for (const match of source.matchAll(pattern)) {
        calls.push(match[0]);
        expect(match[0]).not.toContain('credentials: "omit"');
        expect(match[0]).not.toContain("credentials: 'omit'");
      }
    }
    expect(calls.length).toBeGreaterThan(0);
  });
});
