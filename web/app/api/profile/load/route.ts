import { NextResponse } from 'next/server';

const serverBase = process.env.PY_SERVER_URL || 'http://localhost:8001';

export async function GET() {
  try {
    const response = await fetch(`${serverBase}/api/v1/profile/load`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { ok: false, error: data.detail || 'Failed to load profile' },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { ok: false, error: error.message || 'Failed to load profile' },
      { status: 500 }
    );
  }
}
