import { NextResponse } from "next/server";

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const action = String(body?.action || "start");

    let endpoint = "/api/verify/start";

    if (action === "continue") {
      if (!body.task_id) {
        return NextResponse.json({ success: false, error: "task_id is required for continue" }, { status: 400 });
      }
      endpoint = `/api/verify/continue/${body.task_id}`;
    } else if (action === "resend_cookies") {
      if (!body.task_id) {
        return NextResponse.json({ success: false, error: "task_id is required for resend_cookies" }, { status: 400 });
      }
      if (!body.cookies) {
        return NextResponse.json({ success: false, error: "Cookies are required for resend_cookies" }, { status: 400 });
      }
      endpoint = `/api/verify/resend_cookies/${body.task_id}`;
    } else if (action === "cancel") {
      if (!body.task_id) {
        return NextResponse.json({ success: false, error: "task_id is required for cancel" }, { status: 400 });
      }
      endpoint = `/api/verify/cancel/${body.task_id}`;
    }

    // Validasi basic sebelum lempar ke ptero
    if (action === "start" && !body.cookies) {
      return NextResponse.json({ success: false, error: "Cookies are required" }, { status: 400 });
    }

    console.log("Sending POST to bot server...");
    const res = await fetch(`${process.env.PTERO_API_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.API_SECRET}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: 'no-store'
    });

    const text = await res.text();
    try {
        const data = JSON.parse(text);
        if (!res.ok) {
          return NextResponse.json(data, { status: res.status });
        }
        return NextResponse.json(data);
    } catch {
        if (!res.ok) {
          return NextResponse.json({ success: false, error: "Bot server logic error" }, { status: res.status });
        }
        return NextResponse.json({ success: false, error: "Failed to parse bot POST response" }, { status: 500 });
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Connection to bot server failed";
    console.error("Fetch POST error:", error);
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
