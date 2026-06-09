import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const flow = searchParams.get("flow") || "login"; // "login" or "connect"
  const email = searchParams.get("email") || "";

  const redirectUri = process.env.INSTAGRAM_REDIRECT_URI;
  if (!redirectUri) {
    return NextResponse.json({ error: "Instagram not configured" }, { status: 500 });
  }

  // LOGIN → native "Instagram API with Instagram Login" (instagram.com/oauth).
  // Authenticates the user directly with their Instagram account; no Facebook Page.
  if (flow === "login") {
    const igAppId = process.env.INSTAGRAM_APP_ID;
    if (!igAppId) {
      return NextResponse.json({ error: "Instagram login not configured" }, { status: 500 });
    }
    const url = new URL("https://www.instagram.com/oauth/authorize");
    url.searchParams.set("client_id", igAppId);
    url.searchParams.set("redirect_uri", redirectUri);
    url.searchParams.set("response_type", "code");
    url.searchParams.set("scope", "instagram_business_basic");
    url.searchParams.set("state", "login");
    return NextResponse.json({ url: url.toString() });
  }

  // CONNECT (automation setup) → unchanged Facebook-for-Business OAuth.
  const appId = process.env.FACEBOOK_APP_ID;
  if (!appId) {
    return NextResponse.json({ error: "Instagram not configured" }, { status: 500 });
  }
  const url = new URL("https://www.facebook.com/v18.0/dialog/oauth");
  url.searchParams.set("client_id", appId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("state", encodeURIComponent(email));
  url.searchParams.set("scope", "pages_show_list,pages_read_engagement,instagram_basic,instagram_manage_comments,public_profile");
  url.searchParams.set("response_type", "code");

  return NextResponse.json({ url: url.toString() });
}
