import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  try {
    const path = params.path.join('/');
    const imageUrl = `${process.env.NEXT_PUBLIC_API_URL}/static/${path}`;
    
    const response = await fetch(imageUrl);
    const buffer = await response.arrayBuffer();
    
    return new NextResponse(buffer, {
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'image/jpeg',
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    });
  } catch (error) {
    console.error('Image fetch error:', error);
    return new NextResponse('Image not found', { status: 404 });
  }
}
