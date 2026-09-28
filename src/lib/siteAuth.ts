export const SITE_AUTH_COOKIE = "site_auth";
export const SITE_AUTH_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

const TOKEN_MESSAGE = "darryl-land-search-site-gate-v1";

/** Empty and missing both fail closed. The value is never written into the repo. */
export function readSitePassword(): string | null {
  const value = process.env.SITE_PASSWORD;
  if (typeof value !== "string" || value.length === 0) return null;
  return value;
}

function toHex(bytes: Uint8Array): string {
  let hex = "";
  for (const byte of bytes) hex += byte.toString(16).padStart(2, "0");
  return hex;
}

/** HMAC-SHA256 of a fixed message, keyed by the site password. Not the password itself. */
export async function siteAuthToken(password: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(password),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(TOKEN_MESSAGE));
  return toHex(new Uint8Array(signature));
}

/**
 * Constant-time string compare. Length differences still return false, and the
 * loop always runs so a mismatch does not stop at the first byte.
 */
export function timingSafeEqualString(a: string, b: string): boolean {
  const aBytes = new TextEncoder().encode(a);
  const bBytes = new TextEncoder().encode(b);
  const length = Math.max(aBytes.length, bBytes.length, 1);
  let diff = aBytes.length === bBytes.length ? 0 : 1;
  for (let i = 0; i < length; i++) {
    const aByte = aBytes[i] ?? 0;
    const bByte = bBytes[i] ?? 0;
    diff |= aByte ^ bByte;
  }
  return diff === 0;
}

/** Returns the cookie token when the submitted password matches, otherwise null. */
export async function loginToken(submitted: string, expected: string | null): Promise<string | null> {
  if (!expected) {
    await siteAuthToken(submitted || "x");
    return null;
  }
  const [got, want] = await Promise.all([siteAuthToken(submitted), siteAuthToken(expected)]);
  if (!timingSafeEqualString(got, want)) return null;
  return want;
}

export async function cookieAuthorizes(cookieValue: string | undefined, password: string | null): Promise<boolean> {
  if (!password || !cookieValue) return false;
  const expected = await siteAuthToken(password);
  return timingSafeEqualString(cookieValue, expected);
}
