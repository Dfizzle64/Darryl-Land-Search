import { NextResponse } from "next/server";
import { SITE_AUTH_COOKIE, SITE_AUTH_MAX_AGE_SECONDS, loginToken, readSitePassword } from "@/lib/siteAuth";

export async function POST(request: Request) {
  let submitted = "";
  try {
    const body: unknown = await request.json();
    if (body && typeof body === "object" && "password" in body && typeof (body as { password: unknown }).password === "string") {
      submitted = (body as { password: string }).password;
    }
  } catch {
    submitted = "";
  }

  const token = await loginToken(submitted, readSitePassword());
  if (!token) {
    return NextResponse.json({ error: "Incorrect password" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: SITE_AUTH_COOKIE,
    value: token,
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: SITE_AUTH_MAX_AGE_SECONDS,
  });
  return response;
}
