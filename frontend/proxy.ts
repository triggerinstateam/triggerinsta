import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

export async function proxy(req: NextRequest) {
  const token = await getToken({ 
    req, 
    secret: process.env.AUTH_SECRET,
    cookieName: process.env.NODE_ENV === "production" ? "__Secure-next-auth.session-token" : "next-auth.session-token"
  });
  const { pathname } = req.nextUrl;

  const isLoggedIn = !!token;
  const isProtectedRoute = pathname.startsWith("/dashboard");
  const isAuthRoute = pathname === "/login" || pathname === "/signup";

  if (isProtectedRoute && !isLoggedIn) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  if (isAuthRoute && isLoggedIn) {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/signup"],
};
