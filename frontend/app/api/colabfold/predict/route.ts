import { NextRequest, NextResponse } from "next/server";

// Allow this route to run up to 15 min (e.g. Vercel Pro). Omit or reduce on free tier.
export const maxDuration = 900;

const PREDICT_URL = (
  process.env.NEXT_PUBLIC_COLABFOLD_PREDICT_URL ||
  process.env.COLABFOLD_PREDICT_URL ||
  ""
).replace(/\/$/, ""); // no trailing slash (Modal 404s with trailing slash)

export async function POST(request: NextRequest) {
  if (!PREDICT_URL.trim()) {
    return NextResponse.json(
      { error: "ColabFold endpoint not configured. Set NEXT_PUBLIC_COLABFOLD_PREDICT_URL or COLABFOLD_PREDICT_URL." },
      { status: 503 }
    );
  }

  let body: { sequence?: string; job_name?: string; num_models?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const sequence = typeof body.sequence === "string" ? body.sequence.trim() : "";
  if (!sequence) {
    return NextResponse.json({ error: "Missing or empty sequence" }, { status: 400 });
  }

  const base = PREDICT_URL.replace(/\/$/, "");
  const postBody = JSON.stringify({
    sequence,
    job_name: body.job_name ?? "viewer",
    num_models: body.num_models ?? 1,
  });
  const postOpts = {
    method: "POST" as const,
    headers: { "Content-Type": "application/json" },
    body: postBody,
    signal: AbortSignal.timeout(30 * 1000),
  };

  try {
    console.log("[DEBUG predict] POST submit URL:", base, "sequence length:", sequence.length);
    // Spawn: POST returns job_id. Try base, then base/, then base/predict (some gateways 404 on root)
    let spawnRes = await fetch(base, postOpts);
    console.log("[DEBUG predict] submit response status:", spawnRes.status, spawnRes.statusText);
    if (spawnRes.status === 404) {
      spawnRes = await fetch(`${base}/`, postOpts);
      console.log("[DEBUG predict] retry with / status:", spawnRes.status);
    }
    if (spawnRes.status === 404) {
      spawnRes = await fetch(`${base}/predict`, postOpts);
      console.log("[DEBUG predict] retry with /predict status:", spawnRes.status);
    }
    const spawnRaw = await spawnRes.text();
    console.log("[DEBUG predict] submit raw response length:", spawnRaw.length, "first 200:", spawnRaw.slice(0, 200));
    let spawnData: { job_id?: string; error?: string };
    try {
      spawnData = spawnRaw.length > 0 ? JSON.parse(spawnRaw) : {};
    } catch {
      return NextResponse.json(
        {
          error: spawnRes.ok
            ? "ColabFold returned invalid JSON from submit."
            : spawnRes.status === 404
              ? "ColabFold 404: Set NEXT_PUBLIC_COLABFOLD_PREDICT_URL in frontend/.env.local to the 'web' URL from 'modal serve', then restart Next.js."
              : `ColabFold submit error (${spawnRes.status}). Ensure the Modal app uses spawn + poll (POST returns job_id).`,
        },
        { status: 502 }
      );
    }
    if (!spawnRes.ok) {
      const errMsg =
        spawnRes.status === 404
          ? "ColabFold 404: In frontend/.env.local set NEXT_PUBLIC_COLABFOLD_PREDICT_URL to the exact 'web' URL from 'modal serve' (e.g. https://YOUR_WORKSPACE--colabfold-genaigenesis-web-dev.modal.run). Restart the Next.js dev server after changing."
          : spawnData?.error ?? `Upstream error: ${spawnRes.status}`;
      return NextResponse.json(
        { error: errMsg },
        { status: spawnRes.status >= 500 ? 502 : spawnRes.status }
      );
    }
    const jobId = spawnData.job_id;
    if (!jobId || typeof jobId !== "string") {
      console.log("[DEBUG predict] no job_id in response:", spawnData);
      return NextResponse.json(
        { error: "ColabFold did not return job_id. Ensure the Modal app uses spawn + poll." },
        { status: 502 }
      );
    }
    console.log("[DEBUG predict] returning job_id:", jobId.slice(0, 24) + "...");
    // Return immediately; client polls GET /api/colabfold/result?job_id= until done (avoids long-lived connection)
    return NextResponse.json({ job_id: jobId });
  } catch (e) {
    const err = e instanceof Error ? e : new Error(String(e));
    const message = err.message;
    const code = "code" in err ? String((err as NodeJS.ErrnoException).code) : "";
    const isTimeout = message.toLowerCase().includes("timeout") || message.toLowerCase().includes("abort");
    let friendlyMessage: string;
    if (isTimeout) {
      friendlyMessage = "ColabFold is still running (cold start can take 3–5 min). Wait a minute and try again.";
    } else if (message.includes("fetch") || message.includes("Failed to fetch") || code === "ECONNREFUSED" || code === "ENOTFOUND" || code === "ETIMEDOUT") {
      friendlyMessage = "Could not reach ColabFold. Check that \"modal serve\" is running and NEXT_PUBLIC_COLABFOLD_PREDICT_URL in .env.local matches the predict URL (e.g. …-predict-dev.modal.run).";
      if (process.env.NODE_ENV === "development" && code) {
        friendlyMessage += ` (${code})`;
      }
    } else {
      friendlyMessage = message;
    }
    return NextResponse.json({ error: friendlyMessage }, { status: 502 });
  }
}
