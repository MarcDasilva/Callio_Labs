import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 300;

const LANGFLOW_BASE_URL = (
  process.env.LANGFLOW_BASE_URL || "http://127.0.0.1:7860"
).replace(/\/$/, "");

const LANGFLOW_FLOW_ID =
  process.env.LANGFLOW_FLOW_ID ||
  "9d638972-17ba-45e2-8d7b-a688d87c0f11";

const LANGFLOW_API_KEY = process.env.LANGFLOW_API_KEY || "";

let cachedToken: { token: string; expires: number } | null = null;

async function getAuthToken(): Promise<string> {
  if (LANGFLOW_API_KEY) return LANGFLOW_API_KEY;
  if (cachedToken && Date.now() < cachedToken.expires) return cachedToken.token;

  try {
    const res = await fetch(`${LANGFLOW_BASE_URL}/api/v1/auto_login`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return "";
    const data = await res.json();
    const token = data.access_token ?? "";
    if (token) {
      cachedToken = { token, expires: Date.now() + 30 * 60 * 1000 };
    }
    return token;
  } catch {
    return "";
  }
}

async function langflowHeaders(): Promise<Record<string, string>> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const token = await getAuthToken();
  if (token) {
    if (token.startsWith("sk-")) {
      h["x-api-key"] = token;
    } else {
      h["Authorization"] = `Bearer ${token}`;
    }
  }
  return h;
}

export async function POST(request: NextRequest) {
  let body: { input_value?: string; session_id?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const inputValue =
    typeof body.input_value === "string" ? body.input_value.trim() : "";
  if (!inputValue) {
    return NextResponse.json(
      { error: "Missing or empty input_value" },
      { status: 400 },
    );
  }

  const headers = await langflowHeaders();

  let jobId: string;
  try {
    const buildUrl = `${LANGFLOW_BASE_URL}/api/v1/build/${LANGFLOW_FLOW_ID}/flow`;
    const buildRes = await fetch(buildUrl, {
      method: "POST",
      headers,
      body: JSON.stringify({
        inputs: {
          input_value: inputValue,
          type: "chat",
          ...(body.session_id ? { session: body.session_id } : {}),
        },
      }),
      signal: AbortSignal.timeout(15_000),
    });

    if (!buildRes.ok) {
      const text = await buildRes.text();
      console.error("[langflow] build error:", buildRes.status, text.slice(0, 500));
      return NextResponse.json(
        {
          error:
            buildRes.status === 404
              ? `Flow not found (${LANGFLOW_FLOW_ID}).`
              : `Langflow error (${buildRes.status}): ${text.slice(0, 200)}`,
        },
        { status: 502 },
      );
    }

    const buildData = await buildRes.json();
    jobId = buildData.job_id;
    if (!jobId) {
      return NextResponse.json(
        { error: "Langflow did not return a job_id" },
        { status: 502 },
      );
    }
  } catch (e) {
    const err = e instanceof Error ? e : new Error(String(e));
    if (err.message.includes("ECONNREFUSED") || err.message.includes("fetch")) {
      return NextResponse.json(
        { error: "Could not reach Langflow. Make sure it's running." },
        { status: 502 },
      );
    }
    return NextResponse.json({ error: err.message }, { status: 502 });
  }

  const eventsUrl = `${LANGFLOW_BASE_URL}/api/v1/build/${jobId}/events`;

  try {
    const eventsRes = await fetch(eventsUrl, {
      headers,
      signal: AbortSignal.timeout(240_000),
    });

    if (!eventsRes.ok || !eventsRes.body) {
      return NextResponse.json(
        { error: `Failed to stream events: ${eventsRes.status}` },
        { status: 502 },
      );
    }

    const upstream = eventsRes.body;
    const decoder = new TextDecoder();
    const encoder = new TextEncoder();
    const reader = upstream.getReader();

    let lineBuffer = "";
    let sessionId: string | null = null;
    let lastFinalText = "";

    const stream = new ReadableStream({
      async start(controller) {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            lineBuffer += decoder.decode(value, { stream: true });
            const lines = lineBuffer.split("\n");
            lineBuffer = lines.pop() ?? "";

            for (const rawLine of lines) {
              const line = rawLine.trim();
              if (!line) continue;

              try {
                const evt = JSON.parse(line);
                const eventType: string = evt.event ?? "";
                const data = evt.data ?? {};

                if (eventType === "add_message") {
                  const sender = data.sender ?? "";
                  const senderName = data.sender_name ?? "";
                  const text: string = data.text ?? "";
                  if (sender === "User" || senderName === "User") continue;
                  if (!text) continue;
                  if (isPrimerResultJson(text)) continue;
                  if (data.session_id) sessionId = data.session_id;

                  lastFinalText = text;
                  controller.enqueue(
                    encoder.encode(
                      JSON.stringify({
                        type: "step",
                        step: {
                          type: "thinking",
                          label: senderName || "Agent",
                          content: stripEmbeddedPrimerJson(text),
                        },
                      }) + "\n",
                    ),
                  );
                } else if (eventType === "token") {
                  const chunk = data.chunk ?? "";
                  if (chunk) {
                    controller.enqueue(
                      encoder.encode(
                        JSON.stringify({ type: "token", chunk }) + "\n",
                      ),
                    );
                  }
                } else if (eventType === "end_vertex") {
                  const buildData = data.build_data ?? data;
                  const vertexId: string = buildData.id ?? "";
                  if (vertexId.startsWith("ChatInput")) continue;

                  const vertexData = buildData.data ?? {};
                  const outputs = vertexData.outputs ?? {};
                  const message = vertexData.message;

                  let label = vertexId.split("-")[0];
                  let stepType: "thinking" | "tool_call" | "output" = "thinking";

                  if (vertexId.startsWith("Agent")) {
                    label = message?.sender_name ?? "Agent";
                  } else if (vertexId.startsWith("Prompt")) {
                    label = "Prompt";
                    const promptText = outputs?.prompt?.message;
                    if (promptText && typeof promptText === "string") {
                      controller.enqueue(
                        encoder.encode(
                          JSON.stringify({
                            type: "step",
                            step: {
                              type: "thinking",
                              label: "Preparing prompt",
                              content:
                                promptText.length > 300
                                  ? promptText.slice(0, 300) + "…"
                                  : promptText,
                            },
                          }) + "\n",
                        ),
                      );
                    }
                    continue;
                  } else if (
                    vertexId.includes("Tool") ||
                    vertexId.includes("MCP") ||
                    vertexId.includes("Primer3") ||
                    vertexId.includes("Search") ||
                    vertexId.includes("WebSearch")
                  ) {
                    stepType = "tool_call";
                  } else if (vertexId.startsWith("ChatOutput")) {
                    stepType = "output";
                    label = "Output";
                    const msgText =
                      message?.message ?? outputs?.message?.message ?? "";
                    if (msgText && !isPrimerResultJson(msgText)) {
                      lastFinalText = stripEmbeddedPrimerJson(msgText);
                    }
                    continue;
                  } else if (vertexId.startsWith("OpenAIModel") || vertexId.startsWith("LanguageModel")) {
                    continue;
                  }

                  const duration = vertexData.duration ?? "";
                  controller.enqueue(
                    encoder.encode(
                      JSON.stringify({
                        type: "step",
                        step: {
                          type: stepType,
                          label,
                          content: duration
                            ? `${label} completed (${duration})`
                            : `${label} completed`,
                        },
                      }) + "\n",
                    ),
                  );
                } else if (eventType === "error") {
                  const rawError = data.error;
                  const rawText = data.text ?? "";
                  let errorStr = "";
                  if (typeof rawError === "string" && rawError) {
                    errorStr = rawError;
                  } else if (typeof rawText === "string" && rawText.trim()) {
                    errorStr = rawText.trim();
                  } else if (data.message && typeof data.message === "string") {
                    errorStr = data.message;
                  }
                  if (errorStr) {
                    controller.enqueue(
                      encoder.encode(
                        JSON.stringify({
                          type: "error",
                          error: errorStr.slice(0, 500),
                        }) + "\n",
                      ),
                    );
                  }
                }
              } catch {
                // skip unparseable event lines
              }
            }
          }
        } catch (e) {
          try {
            controller.enqueue(
              encoder.encode(
                JSON.stringify({
                  type: "error",
                  error: e instanceof Error ? e.message : "Stream error",
                }) + "\n",
              ),
            );
          } catch { /* controller may be closed */ }
        }

        try {
          controller.enqueue(
            encoder.encode(
              JSON.stringify({
                type: "end",
                message:
                  stripEmbeddedPrimerJson(lastFinalText) || "Flow completed.",
                session_id: sessionId,
              }) + "\n",
            ),
          );
          controller.close();
        } catch { /* already closed */ }
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (e) {
    const err = e instanceof Error ? e : new Error(String(e));
    return NextResponse.json({ error: err.message }, { status: 502 });
  }
}

function isPrimerResultJson(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return false;
  try {
    const obj = JSON.parse(trimmed);
    if (obj && typeof obj === "object") {
      if (
        Array.isArray(obj.results) &&
        obj.results.some(
          (r: Record<string, unknown>) => Array.isArray(r.pairs),
        )
      )
        return true;
      if (Array.isArray(obj.pairs)) return true;
      if (obj.forward_primer || obj.reverse_primer) return true;
    }
  } catch {
    // not JSON
  }
  return false;
}

function stripEmbeddedPrimerJson(text: string): string {
  return text
    .replace(
      /```(?:json)?\s*\n?\{[\s\S]*?"(?:pairs|forward_primer|reverse_primer)"[\s\S]*?\}\s*\n?```/g,
      "[Primer results available]",
    )
    .replace(
      /\{[\s\S]{50,}?"pairs"\s*:\s*\[[\s\S]*?\]\s*[\s\S]*?\}/g,
      (match) => {
        if (isPrimerResultJson(match)) return "[Primer results available]";
        return match;
      },
    );
}
