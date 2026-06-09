import { NextResponse } from "next/server";
import { callBackend } from "@/app/lib/backendServer";

// The Graph API token exchange + Instagram account resolution + user persistence
// now lives in Django (POST /api/instagram/oauth/exchange). This route keeps the
// browser-facing redirect + NextAuth session handshake.
export async function GET(request: Request) {
  const baseUrl = process.env.NEXTAUTH_URL || "http://localhost:3000";
  try {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const error = searchParams.get("error");

    if (error) return NextResponse.redirect(new URL("/login?error=access_denied", baseUrl));
    if (!code || !state) return NextResponse.redirect(new URL("/login?error=invalid_request", baseUrl));

    const decodedState = decodeURIComponent(state);

    // LOGIN → native Instagram login exchange (instagram.com / graph.instagram.com).
    // CONNECT (state = email) → unchanged Facebook-for-Business exchange.
    const isLogin = decodedState === "login";
    const endpoint = isLogin ? "/instagram/login/exchange" : "/instagram/oauth/exchange";

    const res = await callBackend(endpoint, {
      method: "POST",
      body: JSON.stringify({ code, state: decodedState }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "OAuth exchange failed");

    if (data.isLoginFlow) {
      // Hand off to the client signin page which establishes the NextAuth session.
      const params = new URLSearchParams({
        email: data.email,
        name: data.name || "",
        image: data.image || "",
      });
      return NextResponse.redirect(new URL(`/api/auth/instagram/signin?${params}`, baseUrl));
    }

    return NextResponse.redirect(new URL("/dashboard/instagram?success=connected", baseUrl));
  } catch (error: any) {
    console.error("Instagram OAuth callback error:", error);
    return NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(error.message)}`, baseUrl));
  }
}
