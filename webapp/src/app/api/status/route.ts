import { NextResponse } from "next/server";

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  try {
    const url = `${process.env.PTERO_API_URL}/api/verify/status`;
    console.log("Fetching URL:", url);
    const res = await fetch(url, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${process.env.API_SECRET}`,
        "Content-Type": "application/json",
      },
      cache: 'no-store'
    });

    if (!res.ok) {
      console.error(`Status ${res.status} from API`);
      return NextResponse.json({ success: false, error: "Bot server error" }, { status: res.status });
    }

    const text = await res.text();
    try {
        const data = JSON.parse(text);
        return NextResponse.json(data);
    } catch {
        console.error("JSON parse error. Raw text:", text);
        return NextResponse.json({ success: false, error: "Failed to parse bot response" }, { status: 500 });
    }
  } catch (error: unknown) {
    const details = error instanceof Error ? error.message : String(error);
    console.error("Fetch error details:", error);
    return NextResponse.json({ success: false, error: "Connection to bot server failed", details }, { status: 500 });
  }
}
