import { NextRequest, NextResponse } from 'next/server';

const resolveServerBase = () =>
  process.env['PY_SERVER_URL'] || process.env['NEXT_PUBLIC_PY_SERVER_URL'] || 'http://localhost:8001';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const serverBase = resolveServerBase();

    const response = await fetch(`${serverBase}/api/v1/profile/save`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || 'Failed to save profile' },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || 'Failed to save profile' },
      { status: 500 }
    );
  }
}
