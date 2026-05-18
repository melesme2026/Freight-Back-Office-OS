import { NextResponse, type NextRequest } from "next/server";

import { SURFACES } from "@/lib/surfaces";

function normalizeHost(request: NextRequest): string {
  return (request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? "")
    .split(":")[0]
    .trim()
    .toLowerCase();
}

function redirectTo(request: NextRequest, pathname: string): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = pathname;
  url.search = "";
  return NextResponse.redirect(url);
}

export function middleware(request: NextRequest) {
  const host = normalizeHost(request);
  const { pathname } = request.nextUrl;

  if (pathname !== "/") {
    return NextResponse.next();
  }

  if (host === SURFACES.staff.productionHost) {
    return redirectTo(request, SURFACES.staff.loginRoute);
  }

  if (host === SURFACES.driver.productionHost) {
    return redirectTo(request, SURFACES.driver.loginRoute);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/"],
};
