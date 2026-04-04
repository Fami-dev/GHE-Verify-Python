import { NextResponse } from "next/server";

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const resolvedParams = await params;
    const url = `${process.env.PTERO_API_URL}/api/user/${resolvedParams.id}`;
    
    const res = await fetch(url, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${process.env.API_SECRET}`,
        "Content-Type": "application/json",
      },
      cache: 'no-store'
    });

    if (!res.ok) {
      return NextResponse.json({ success: false, error: "Bot server logic error" }, { status: res.status });
    }

    const text = await res.text();
    try {
        const data = JSON.parse(text);
        return NextResponse.json(data);
    } catch {
        return NextResponse.json({ success: false, error: "Failed to parse bot user response" }, { status: 500 });
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Connection to bot server failed";
    console.error("Fetch user POST error:", error);
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
