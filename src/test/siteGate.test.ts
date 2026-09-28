import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "../app/api/login/route";
import { middleware } from "../middleware";
import { authToken, gateRequest, sitePassword, tokensMatch } from "../lib/siteAuth";
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
  it("derives a fixed-length HMAC and not the password itself", () => {
    const token = authToken("correct-horse");
    expect(token).toMatch(/^[0-9a-f]{64}$/);
    expect(token).not.toContain("correct-horse");
    expect(authToken("correct-horse")).toBe(token);
    expect(authToken("other-horse")).not.toBe(token);
  });

  it("compares tokens in constant time and rejects length mismatches", () => {
    const token = authToken("correct-horse");
    expect(tokensMatch(token, token)).toBe(true);
    expect(tokensMatch(authToken("other-horse"), token)).toBe(false);
    expect(tokensMatch("short", token)).toBe(false);
    expect(tokensMatch("correct-horse", token)).toBe(false);
  });

  it("treats an unset or empty SITE_PASSWORD as closed", () => {
    delete process.env.SITE_PASSWORD;
    expect(sitePassword()).toBeNull();
    process.env.SITE_PASSWORD = "";
    expect(sitePassword()).toBeNull();
    process.env.SITE_PASSWORD = "correct-horse";
    expect(sitePassword()).toBe("correct-horse");
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
  const password = "correct-horse";
  const cookie = authToken(password);

  it("allows the login page, login API, and login assets without a cookie", () => {
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
      expect(gateRequest({ pathname, search: "", cookie: undefined, password: null }).action).toBe("allow");
    }
  });

  it("fails closed when the password is unset", () => {
    expect(gateRequest({ pathname: "/", search: "", cookie, password: null })).toEqual({
      action: "redirect",
      next: "/",
    });
    expect(gateRequest({ pathname: "/api/parcels", search: "?minAcres=5", cookie, password: null }).action).toBe(
      "unauthorized",
    );
  });

  it("redirects pages and rejects API routes until the cookie matches", () => {
    expect(gateRequest({ pathname: "/", search: "?market=Orlando", cookie: undefined, password })).toEqual({
      action: "redirect",
      next: "/?market=Orlando",
    });
    expect(gateRequest({ pathname: "/api/geocode", search: "?q=orlando", cookie: "nope", password }).action).toBe(
      "unauthorized",
    );
    expect(gateRequest({ pathname: "/api/parcels/abc", search: "", cookie, password }).action).toBe("allow");
    expect(gateRequest({ pathname: "/", search: "", cookie, password }).action).toBe("allow");
  });

  it("invalidates cookies when the password changes", () => {
    expect(gateRequest({ pathname: "/api/parcel-coverage", search: "", cookie, password: "new-password" }).action).toBe(
      "unauthorized",
    );
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
  it("sets the HMAC cookie on the correct password", async () => {
    process.env.SITE_PASSWORD = "correct-horse";
    const response = await POST(
      new Request("http://localhost/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: "correct-horse" }),
      }),
    );
    expect(response.status).toBe(200);
    const setCookie = response.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain(`${SITE_AUTH_COOKIE}=${authToken("correct-horse")}`);
    expect(setCookie).not.toContain("correct-horse");
    expect(setCookie.toLowerCase()).toContain("httponly");
    expect(setCookie.toLowerCase()).toContain("secure");
    expect(setCookie.toLowerCase()).toContain("samesite=lax");
    expect(setCookie).toContain("Max-Age=2592000");
  });

  it("returns Incorrect password for a wrong password and when unset", async () => {
    process.env.SITE_PASSWORD = "correct-horse";
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

    delete process.env.SITE_PASSWORD;
    const closed = await POST(
      new Request("http://localhost/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: "correct-horse" }),
      }),
    );
    expect(closed.status).toBe(401);
    expect(await closed.json()).toEqual({ error: "Incorrect password" });
    expect(closed.headers.get("set-cookie")).toBeNull();
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
    process.env.SITE_PASSWORD = "correct-horse";
    const request = new NextRequest("http://localhost:3000/api/geocode?q=orlando", {
      headers: { cookie: `${SITE_AUTH_COOKIE}=${authToken("correct-horse")}` },
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
