import { NextResponse } from "next/server";
import { expectedPasswordHash, passwordDigest, sessionToken, tokensMatch } from "@/lib/siteAuth";
import { SITE_AUTH_COOKIE, siteAuthCookieOptions } from "@/lib/siteGate";

export async function POST(request: Request) {
  let submitted = "";
  try {
    const body = (await request.json()) as { password?: unknown };
    if (body && typeof body.password === "string") submitted = body.password;
  } catch {
    submitted = "";
  }

  // Compare hashes, not the password. The cookie is an HMAC of that hash.
  const expectedHash = expectedPasswordHash();
  const submittedHash = passwordDigest(submitted);
  if (!tokensMatch(submittedHash, expectedHash)) {
    return NextResponse.json(
      { error: "Incorrect password" },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }

  const response = NextResponse.json({ ok: true }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set(SITE_AUTH_COOKIE, sessionToken(expectedHash), siteAuthCookieOptions());
  return response;
}
