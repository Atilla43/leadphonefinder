import { NextRequest, NextResponse } from "next/server";

const protectedPaths = [
  "/dashboard",
  "/conversations",
  "/campaigns",
  "/settings",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if this is a protected route
  const isProtected = protectedPaths.some(
    (path) => pathname === path || pathname.startsWith(path + "/")
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  // Check for auth token in cookie
  const token = request.cookies.get("sg_token")?.value;

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/conversations/:path*",
    "/campaigns/:path*",
    "/settings/:path*",
  ],
};
