import { NextResponse, type NextRequest } from "next/server";
import { gateRequest } from "./lib/siteAuth";
import { SITE_AUTH_COOKIE } from "./lib/siteGate";

/**
 * Site-wide password gate. Node.js runtime so an optional SITE_PASSWORD
 * override is read on each request. The built-in hash works when it is unset.
 */
export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const decision = gateRequest({
    pathname,
    search,
    cookie: request.cookies.get(SITE_AUTH_COOKIE)?.value,
  });

  if (decision.action === "allow") return NextResponse.next();

  if (decision.action === "unauthorized") {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = "";
  loginUrl.searchParams.set("next", decision.next);
  const response = NextResponse.redirect(loginUrl);
  response.headers.set("Cache-Control", "no-store");
  return response;
}

export const config = {
  runtime: "nodejs",
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg|catalyst-logo.webp).*)"],
};
