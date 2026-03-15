import { NextRequest, NextResponse } from "next/server";

const PREDICT_URL = (
  process.env.NEXT_PUBLIC_COLABFOLD_PREDICT_URL ||
  process.env.COLABFOLD_PREDICT_URL ||
  ""
).replace(/\/$/, "");

const RESULT_URL = (
  process.env.NEXT_PUBLIC_COLABFOLD_RESULT_URL ||
  process.env.COLABFOLD_RESULT_URL ||
  (PREDICT_URL ? `${PREDICT_URL}/result` : "")
).replace(/\/$/, "");

export async function GET(request: NextRequest) {
  if (!RESULT_URL.trim()) {
    return NextResponse.json(
      { error: "ColabFold result endpoint not configured. Set NEXT_PUBLIC_COLABFOLD_PREDICT_URL (result URL is derived as .../result) or NEXT_PUBLIC_COLABFOLD_RESULT_URL." },
      { status: 503 }
    );
  }

  const jobId = request.nextUrl.searchParams.get("job_id");
  if (!jobId) {
    return NextResponse.json({ error: "Missing job_id query parameter" }, { status: 400 });
  }

  try {
    const url = `${RESULT_URL}?job_id=${encodeURIComponent(jobId)}`;
    console.log("[DEBUG result] GET", url.slice(0, 80) + "...");
    const res = await fetch(url, {
      method: "GET",
      signal: AbortSignal.timeout(30 * 1000),
    });
    console.log("[DEBUG result] upstream status:", res.status, "ok:", res.ok);

    const raw = await res.text();
    let data: unknown;
    try {
      data = raw.length > 0 ? JSON.parse(raw) : {};
    } catch {
      console.log("[DEBUG result] invalid JSON, raw length:", raw.length, "slice:", raw.slice(0, 150));
      return NextResponse.json(
        { error: "ColabFold result endpoint returned invalid JSON." },
        { status: 502 }
      );
    }
    const hasPdb = typeof data === "object" && data !== null && "pdb" in data;
    const hasError = typeof data === "object" && data !== null && "error" in data;
    console.log("[DEBUG result] hasPdb:", hasPdb, "hasError:", hasError, "status:", (data as { status?: string }).status);

    // 202 = still running, 200 = done
    if (res.status === 202) {
      return NextResponse.json({ status: "pending" }, { status: 202 });
    }

    if (!res.ok) {
      const err = typeof data === "object" && data !== null && "error" in data ? String((data as { error: unknown }).error) : null;
      console.log("[DEBUG result] returning error:", err ?? res.status);
      return NextResponse.json(
        { error: err ?? `Upstream error: ${res.status}` },
        { status: res.status >= 500 ? 502 : res.status }
      );
    }
    if (hasPdb) {
      console.log("[DEBUG result] returning 200 with pdb length:", typeof (data as { pdb?: string }).pdb === "string" ? (data as { pdb: string }).pdb.length : 0);
    }
    return NextResponse.json(data);
  } catch (e) {
    const message = e instanceof Error ? e.message : "Result request failed";
    console.log("[DEBUG result] fetch threw:", message);
    return NextResponse.json(
      { error: message.includes("fetch") || message.includes("Failed to fetch") ? "Could not reach ColabFold result endpoint." : message },
      { status: 502 }
    );
  }
}
