import { createHmac, timingSafeEqual } from "crypto";
import { isApiPath, isPublicPath, redirectNext, type GateResult } from "./siteGate";

const TOKEN_MESSAGE = "darryl-land-search:site-gate:v1";

export function sitePassword(): string | null {
  const value = process.env.SITE_PASSWORD;
  if (typeof value !== "string" || value.length === 0) return null;
  return value;
}

/** HMAC-SHA256 of a fixed message, keyed by the password. Hex, fixed length. */
export function authToken(password: string): string {
  return createHmac("sha256", password).update(TOKEN_MESSAGE).digest("hex");
}

/** Constant-time compare. Length mismatches fail without throwing. */
export function tokensMatch(provided: string, expected: string): boolean {
  const providedBuf = Buffer.from(provided);
  const expectedBuf = Buffer.from(expected);
  if (providedBuf.length !== expectedBuf.length) {
    timingSafeEqual(expectedBuf, expectedBuf);
    return false;
  }
  return timingSafeEqual(providedBuf, expectedBuf);
}

/**
 * Fail closed when SITE_PASSWORD is unset: the login page still loads, and
 * nothing else does.
 */
export function gateRequest(input: {
  pathname: string;
  search: string;
  cookie: string | undefined;
  password: string | null;
}): GateResult {
  if (isPublicPath(input.pathname)) return { action: "allow" };

  const expected = input.password ? authToken(input.password) : null;
  const provided = input.cookie ?? "";
  if (expected && provided.length > 0 && tokensMatch(provided, expected)) {
    return { action: "allow" };
  }

  if (isApiPath(input.pathname)) return { action: "unauthorized" };
  return { action: "redirect", next: redirectNext(input.pathname, input.search) };
}
