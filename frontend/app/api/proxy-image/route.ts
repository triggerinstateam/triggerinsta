import { NextRequest, NextResponse } from 'next/server';

async function getFreshThumbnailUrl(mediaId: string): Promise<string | null> {
  const accessToken = process.env.PAGE_ACCESS_TOKEN;
  if (!accessToken) return null;
  const res = await fetch(
    `https://graph.facebook.com/v19.0/${mediaId}?fields=media_type,media_url,thumbnail_url&access_token=${accessToken}`,
    { cache: 'no-store' }
  );
  if (!res.ok) return null;
  const data = await res.json();
  console.log("[proxy-image] Fresh media data for", mediaId, data);
  return data.media_type === 'VIDEO' ? data.thumbnail_url : data.media_url;
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const mediaId = searchParams.get('mediaId');
    const fallbackUrl = searchParams.get('url');

    let imageUrl: string | null = null;

    if (mediaId) {
      // Always fetch a fresh URL from Instagram Graph API using mediaId
      imageUrl = await getFreshThumbnailUrl(mediaId);
      console.log("[proxy-image] Fresh thumbnail URL:", imageUrl);
    } else if (fallbackUrl) {
      imageUrl = fallbackUrl;
    }

    if (!imageUrl) {
      return NextResponse.json({ error: 'Could not resolve image URL' }, { status: 400 });
    }

    const res = await fetch(imageUrl, {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
    });

    if (!res.ok) {
      return NextResponse.json({ error: 'Failed to fetch image' }, { status: res.status });
    }

    const buffer = await res.arrayBuffer();

    return new NextResponse(buffer, {
      headers: {
        'Content-Type': res.headers.get('content-type') || 'image/jpeg',
        'Cache-Control': 'public, max-age=3600', // 1 hour cache (not 24h since URLs expire)
      },
    });
  } catch (err) {
    console.error('[proxy-image] Error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
