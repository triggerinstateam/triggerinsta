import { NextRequest, NextResponse } from 'next/server';

interface InstagramMedia {
  id: string;
  shortcode: string;
  permalink: string;
  caption: string;
}

interface InstagramApiResponse {
  data: InstagramMedia[];
  paging?: {
    next?: string;
  };
  error?: {
    message: string;
  };
}

// ─── Step 1 ───────────────────────────────────────────────
function extractShortcode(url: string): string {
  const match = url.match(/instagram\.com\/(?:reel|p|tv)\/([A-Za-z0-9_-]+)/);
  if (!match) throw new Error('Invalid Instagram URL format');
  return match[1];
}

// ─── Step 2 ───────────────────────────────────────────────
async function fetchAllMedia(accountId: string, accessToken: string): Promise<InstagramMedia[]> {
  const media: InstagramMedia[] = [];
  let endpoint: string | null =
    `https://graph.facebook.com/v19.0/${accountId}/media` +
    `?fields=id,shortcode,permalink,caption&limit=100&access_token=${accessToken}`;

  while (endpoint) {
    const res = await fetch(endpoint, { cache: 'no-store' });

    if (!res.ok) {
      const err: InstagramApiResponse = await res.json();
      throw new Error(`Instagram API error: ${err.error?.message ?? res.statusText}`);
    }

    const data: InstagramApiResponse = await res.json();
    media.push(...(data.data ?? []));
    endpoint = data.paging?.next ?? null;
  }

  return media;
}

// ─── Handler ──────────────────────────────────────────────
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const { url } = body as { url?: string };

  if (!url) {
    return NextResponse.json(
      { success: false, error: 'Missing required field: url' },
      { status: 400 }
    );
  }

  // Step 1 — Extract shortcode
  let shortcode: string;
  try {
    shortcode = extractShortcode(url);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to parse URL';
    return NextResponse.json({ success: false, error: message }, { status: 400 });
  }

  const accountId   = process.env.INSTAGRAM_ACCOUNT_ID;
  const accessToken = process.env.PAGE_ACCESS_TOKEN;

  if (!accountId || !accessToken) {
    return NextResponse.json(
      { success: false, error: 'Instagram credentials not configured' },
      { status: 500 }
    );
  }

  try {
    // Step 2 — Fetch media
    const mediaList = await fetchAllMedia(accountId, accessToken);

    // Step 3 — Match shortcode(Check wether url metioned belongs to insta id or not)
    const match = mediaList.find((item) => item.shortcode === shortcode);

    // Step 4 — Return result
    if (!match) {
      return NextResponse.json(
        { success: false, error: 'Media not found in account', shortcode },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success:   true,
      mediaId:   match.id,
      shortcode: match.shortcode,
      permalink: match.permalink,
      caption:   match.caption || '',
    });

  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unexpected error';
    return NextResponse.json({ success: false, error: message }, { status: 502 });
  }
}