"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import GlassSurface from "@/components/GlassSurface";
import {
  IconSend,
  IconLoader2,
  IconBrain,
  IconTool,
  IconMessageCircle,
  IconCube3dSphere,
  IconTerminal,
  IconChevronRight,
  IconDownload,
  IconFileTypePdf,
} from "@tabler/icons-react";
import { isReportContent, downloadReportPdf } from "@/components/report-view";

export interface AgentStep {
  type: "thinking" | "tool_call" | "tool_result" | "output";
  label: string;
  content: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  steps?: AgentStep[];
}

interface ChatbotPanelProps {
  onSend?: () => void;
  messages: ChatMessage[];
  onNewMessage: (userText: string) => void;
  isLoading: boolean;
  onToggleModelView?: () => void;
  modelViewActive?: boolean;
  modelViewContent?: React.ReactNode;
}

const STEP_ICON: Record<AgentStep["type"], typeof IconBrain> = {
  thinking: IconBrain,
  tool_call: IconTool,
  tool_result: IconTerminal,
  output: IconMessageCircle,
};

const STEP_COLOR: Record<AgentStep["type"], string> = {
  thinking: "text-violet-600",
  tool_call: "text-amber-600",
  tool_result: "text-emerald-600",
  output: "text-blue-600",
};

function StepRow({ step }: { step: AgentStep }) {
  const [open, setOpen] = useState(false);
  const Icon = STEP_ICON[step.type];
  const color = STEP_COLOR[step.type];

  return (
    <div className="border-b border-black/4 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left transition-colors hover:bg-black/3"
      >
        <IconChevronRight
          className={`size-3 shrink-0 text-black/30 transition-transform duration-150 ${open ? "rotate-90" : ""}`}
        />
        <Icon className={`size-3 shrink-0 ${color}`} />
        <span className="truncate text-[11px] text-black/60">{step.label}</span>
      </button>
      {open && (
        <div className="px-3 pb-2 pl-8">
          <p className="text-[11px] leading-relaxed text-black/50 whitespace-pre-wrap wrap-break-word">
            {step.content}
          </p>
        </div>
      )}
    </div>
  );
}

function ReportDownloadRow({ markdown }: { markdown: string }) {
  const [busy, setBusy] = useState(false);
  const title = markdown.split("\n")[0]?.replace(/^#+\s*/, "").trim() || "Report";

  const handleClick = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await downloadReportPdf(markdown);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <IconFileTypePdf className="size-5 shrink-0 text-black/50" />
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium text-black">{title}</p>
        <p className="text-[11px] text-black/40">PDF report ready</p>
      </div>
      <button
        type="button"
        onClick={handleClick}
        disabled={busy}
        className="shrink-0 rounded p-1.5 text-black transition-opacity hover:opacity-70 disabled:opacity-50"
        aria-label="Download PDF"
      >
        {busy ? (
          <IconLoader2 className="size-5 animate-spin" />
        ) : (
          <IconDownload className="size-5" />
        )}
      </button>
    </div>
  );
}

export function ChatbotPanel({
  onSend,
  messages,
  onNewMessage,
  isLoading,
  onToggleModelView,
  modelViewActive = false,
  modelViewContent,
}: ChatbotPanelProps) {
  const [input, setInput] = useState("");
  const [showModelViewButton, setShowModelViewButton] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isLoading]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    onSend?.();
    onNewMessage(text);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setShowModelViewButton(true), 3000);
  };

  const hasContent = messages.length > 0 || isLoading;

  return (
    <aside
      className={`w-full max-w-2xl px-4 flex flex-col transition-[gap] duration-300 ${
        showModelViewButton ? "gap-4" : "gap-1"
      }`}
    >
      <GlassSurface
        width={"100%" as unknown as number}
        height={320}
        borderRadius={16}
        backgroundOpacity={0.55}
        className="overflow-hidden"
        contentClassName="!flex !flex-col !items-stretch !justify-start !p-0 !gap-0 !h-full"
      >
        {modelViewActive && modelViewContent ? (
          <div className="h-full w-full">{modelViewContent}</div>
        ) : (
          <div
            ref={scrollRef}
            className="h-full overflow-y-auto"
          >
            {!hasContent && (
              <div className="h-full flex items-center justify-center">
                <p className="text-sm text-black/30">
                  Agent output will appear here…
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id}>
                {msg.role === "user" ? (
                  <div className="flex justify-end px-4 py-2">
                    <div className="max-w-[85%] rounded-xl bg-black/10 px-3.5 py-2 text-sm text-black">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div>
                    {msg.steps && msg.steps.length > 0 && (
                      <div className="border-y border-black/6">
                        {msg.steps.map((step, i) => (
                          <StepRow key={i} step={step} />
                        ))}
                      </div>
                    )}

                    {msg.content ? (
                      isReportContent(msg.content) ? (
                        <ReportDownloadRow markdown={msg.content} />
                      ) : (
                        <div className="px-4 py-3">
                          <div className="text-sm leading-relaxed text-black whitespace-pre-wrap wrap-break-word">
                            {msg.content}
                            {isLoading && msg.id === messages[messages.length - 1]?.id && (
                              <span className="inline-block w-1.5 h-4 ml-0.5 bg-black/40 animate-pulse rounded-sm align-text-bottom" />
                            )}
                          </div>
                        </div>
                      )
                    ) : null}
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 px-3 py-2 border-t border-black/6">
                <IconLoader2 className="size-3 animate-spin text-violet-600" />
                <span className="text-[11px] text-black/50">
                  Agent is working…
                </span>
              </div>
            )}
          </div>
        )}
      </GlassSurface>

      {onToggleModelView && (
        <div
          className={`flex justify-center overflow-hidden transition-all duration-300 ease-out ${
            showModelViewButton
              ? "max-h-16 opacity-100"
              : "max-h-0 opacity-0"
          }`}
        >
          <button
            type="button"
            onClick={onToggleModelView}
            className="flex items-center gap-1.5 rounded-full bg-black/5 px-3 py-1.5 text-xs font-medium text-black/60 transition-colors hover:bg-black/10 hover:text-black/80"
          >
            <IconCube3dSphere className="size-3.5" />
            {modelViewActive ? "Show agent output" : "Show model view"}
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="w-full">
        <GlassSurface
          width={"100%" as unknown as number}
          height={"fit-content" as unknown as number}
          borderRadius={16}
          backgroundOpacity={0.55}
          className="overflow-hidden"
          contentClassName="!flex !flex-col !items-stretch !justify-center !p-0 !gap-0"
        >
          <div className="flex flex-col gap-3 px-4 pt-4 pb-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about genome primer design…"
              className="w-full bg-transparent text-sm text-black placeholder:text-black/50 outline-none md:text-base"
              aria-label="Message"
              disabled={isLoading}
            />
            <div className="flex items-center justify-end gap-2">
              <Button
                type="submit"
                size="icon-sm"
                className="size-8 shrink-0 rounded-lg bg-black/15 text-black hover:bg-black/25"
                disabled={!input.trim() || isLoading}
                aria-label="Send"
              >
                {isLoading ? (
                  <IconLoader2 className="size-4 text-black animate-spin" />
                ) : (
                  <IconSend className="size-4 text-black stroke-[2.5]" />
                )}
              </Button>
            </div>
          </div>
        </GlassSurface>
      </form>
    </aside>
  );
}
