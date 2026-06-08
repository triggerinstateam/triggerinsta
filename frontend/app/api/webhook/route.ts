import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const INTERNAL_SECRET = process.env.INTERNAL_API_SECRET ?? "";

export async function GET(req: NextRequest) {
  const url = `${BACKEND_URL}/api/webhook?${req.nextUrl.searchParams.toString()}`;
  const res = await fetch(url, {
    headers: { "X-Internal-Secret": INTERNAL_SECRET },
  });
  return new Response(await res.text(), { status: res.status });
}

export async function POST(req: NextRequest) {
  const body = await req.text();
  const res = await fetch(`${BACKEND_URL}/api/webhook`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Secret": INTERNAL_SECRET,
    },
    body,
  });
  return new Response(await res.text(), { status: res.status });
}
