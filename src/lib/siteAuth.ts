import { createHash, createHmac, timingSafeEqual } from "crypto";
import { isApiPath, isPublicPath, redirectNext, type GateResult } from "./siteGate";

/** Fixed salt mixed into the password hash. The password itself is not stored. */
export const PASSWORD_SALT = "cdp-land-search:";

/** sha256(PASSWORD_SALT + password). An optional SITE_PASSWORD overrides this. */
export const PASSWORD_HASH = "8c0f2459466b4bd4833382a693823322044c07783f5b781cce906096b160d512";

export function passwordDigest(password: string): string {
  return createHash("sha256").update(PASSWORD_SALT + password).digest("hex");
}

/** Optional override. Empty or unset means the built-in hash is used. */
export function optionalSitePassword(): string | null {
  const value = process.env.SITE_PASSWORD;
  if (typeof value !== "string" || value.length === 0) return null;
  return value;
}

/** Built-in hash, or the hash of SITE_PASSWORD when that override is set. */
export function expectedPasswordHash(): string {
  const override = optionalSitePassword();
  return override ? passwordDigest(override) : PASSWORD_HASH;
}

/**
 * HMAC of the salt, keyed by the password hash. Distinct from both the
 * password and the hash, and it changes when the hash changes.
 */
export function sessionToken(passwordHash: string): string {
  return createHmac("sha256", passwordHash).update(PASSWORD_SALT).digest("hex");
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

export function gateRequest(input: { pathname: string; search: string; cookie: string | undefined }): GateResult {
  if (isPublicPath(input.pathname)) return { action: "allow" };

  const expected = sessionToken(expectedPasswordHash());
  const provided = input.cookie ?? "";
  if (provided.length > 0 && tokensMatch(provided, expected)) return { action: "allow" };

  if (isApiPath(input.pathname)) return { action: "unauthorized" };
  return { action: "redirect", next: redirectNext(input.pathname, input.search) };
}
