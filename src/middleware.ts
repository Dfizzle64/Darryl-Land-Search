import { NextResponse, type NextRequest } from "next/server";
import { isApiPath, isPublicPath } from "@/lib/siteGate";
import { SITE_AUTH_COOKIE, cookieAuthorizes, readSitePassword } from "@/lib/siteAuth";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (isPublicPath(pathname)) return NextResponse.next();

  const password = readSitePassword();
  const cookie = request.cookies.get(SITE_AUTH_COOKIE)?.value;
  if (await cookieAuthorizes(cookie, password)) return NextResponse.next();

  if (isApiPath(pathname)) {
    const denied = NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    denied.headers.set("Cache-Control", "no-store");
    return denied;
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = "";
  loginUrl.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
  const redirect = NextResponse.redirect(loginUrl);
  redirect.headers.set("Cache-Control", "no-store");
  return redirect;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|catalyst-logo.webp).*)"],
};
