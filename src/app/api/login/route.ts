import { NextResponse } from "next/server";
import { authToken, sitePassword, tokensMatch } from "@/lib/siteAuth";
import { SITE_AUTH_COOKIE, siteAuthCookieOptions } from "@/lib/siteGate";

export async function POST(request: Request) {
  const configured = sitePassword();
  let submitted = "";
  try {
    const body = (await request.json()) as { password?: unknown };
    if (body && typeof body.password === "string") submitted = body.password;
  } catch {
    submitted = "";
  }

  // Always hash the submitted value so a missing env var and a wrong password
  // take the same path. The cookie stores the HMAC, not the password.
  const expected = configured ? authToken(configured) : null;
  const actual = authToken(submitted);
  if (!expected || !tokensMatch(actual, expected)) {
    return NextResponse.json(
      { error: "Incorrect password" },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }

  const response = NextResponse.json({ ok: true }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set(SITE_AUTH_COOKIE, expected, siteAuthCookieOptions());
  return response;
}
