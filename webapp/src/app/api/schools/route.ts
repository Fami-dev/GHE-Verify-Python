import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const type = searchParams.get("type") || "student";
    const telegramUserId = searchParams.get("telegram_user_id") || "";

    const url = `${process.env.PTERO_API_URL}/api/schools/list?type=${encodeURIComponent(type)}&telegram_user_id=${encodeURIComponent(telegramUserId)}`;
    const res = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    const text = await res.text();
    try {
      const data = JSON.parse(text);
      return NextResponse.json(data, { status: res.status });
    } catch {
      return NextResponse.json(
        { success: false, error: "Invalid JSON from bot server" },
        { status: 500 },
      );
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 },
    );
  }
}
