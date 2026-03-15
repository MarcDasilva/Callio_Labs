"use client";

import { useCallback, useState } from "react";
import dynamic from "next/dynamic";
import { AppSidebar } from "@/components/app-sidebar";
import {
  ChatbotPanel,
  type ChatMessage,
  type AgentStep,
} from "@/components/chatbot-panel";
import { ProjectsPanel } from "@/components/projects-panel";
import { CallioLabsSplash } from "@/components/callio-labs-splash";
import GlassSurface from "@/components/GlassSurface";
import { SiteHeader } from "@/components/site-header";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
const Dither = dynamic(() => import("@/components/Dither"), { ssr: false });
const PdbViewerOverlay = dynamic(
  () =>
    import("@/components/pdb-viewer-overlay").then((m) => ({
      default: m.PdbViewerOverlay,
    })),
  { ssr: false },
);
const EmbeddedModelViewer = dynamic(
  () =>
    import("@/components/embedded-model-viewer").then((m) => ({
      default: m.EmbeddedModelViewer,
    })),
  { ssr: false },
);

type Page = "study" | "projects";

export function DashboardContent() {
  const [hasStarted, setHasStarted] = useState(false);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [panelsOpen, setPanelsOpen] = useState(false);
  const [activePage, setActivePage] = useState<Page>("study");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [modelViewActive, setModelViewActive] = useState(false);

  const handleNewMessage = useCallback(
    async (userText: string) => {
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: userText,
      };
      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: assistantId, role: "assistant", content: "" },
      ]);
      setIsLoading(true);

      try {
        const res = await fetch("/api/langflow/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            input_value: userText,
            ...(sessionId ? { session_id: sessionId } : {}),
          }),
        });

        const contentType = res.headers.get("content-type") ?? "";

        if (!res.ok) {
          const rawText = await res.text();
          let errorMsg = "Something went wrong";
          try {
            const errData = JSON.parse(rawText);
            errorMsg = errData.error ?? errorMsg;
          } catch {
            errorMsg = rawText || errorMsg;
          }
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: `Error: ${errorMsg}` }
                : m,
            ),
          );
          return;
        }

        if (
          contentType.includes("application/json") &&
          !contentType.includes("text/plain")
        ) {
          const data = await res.json();
          if (data.session_id) setSessionId(data.session_id);
          const steps: AgentStep[] = Array.isArray(data.steps)
            ? data.steps
            : [];
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: data.message ?? "No response received.",
                    steps,
                  }
                : m,
            ),
          );
          return;
        }

        if (!res.body) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: "No response body received." }
                : m,
            ),
          );
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        const processLine = (line: string) => {
          const trimmed = line.trim();
          if (!trimmed) return;

          try {
            const event = JSON.parse(trimmed);

            if (event.type === "step" && event.step) {
              const step = event.step as AgentStep;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, steps: [...(m.steps ?? []), step] }
                    : m,
                ),
              );
            } else if (event.type === "token" && event.chunk) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + event.chunk }
                    : m,
                ),
              );
            } else if (event.type === "end") {
              if (event.session_id) setSessionId(event.session_id);
              const steps: AgentStep[] = Array.isArray(event.steps)
                ? event.steps
                : [];
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content:
                          event.message || m.content || "No response received.",
                        steps: steps.length > 0 ? steps : (m.steps ?? []),
                      }
                    : m,
                ),
              );
            } else if (event.type === "error") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: `Error: ${event.error}` }
                    : m,
                ),
              );
            }
          } catch {
            // skip unparseable lines
          }
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            processLine(line);
          }
        }

        if (buffer.trim()) processLine(buffer);
      } catch (err) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: `Error: ${err instanceof Error ? err.message : "Network error"}`,
                }
              : m,
          ),
        );
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId],
  );

  const headerTitle =
    activePage === "projects" ? "Projects" : "Genome Analysis";

  return (
    <div className="relative h-screen w-full overflow-hidden">
      <CallioLabsSplash />
      <div className="fixed inset-0 z-0 h-screen w-screen">
        <Dither
          waveSpeed={0.02}
          waveFrequency={3}
          waveAmplitude={0.3}
          backgroundColor={[1, 1, 1]}
          waveColor={[0, 0, 0]}
          colorNum={4}
          pixelSize={2}
          enableMouseInteraction
          mouseRadius={1.2}
        />
      </div>
      <div className="relative z-10">
        <SidebarProvider
          className="!bg-transparent"
          style={
            {
              "--sidebar-width": "calc(var(--spacing) * 72)",
              "--header-height": "calc(var(--spacing) * 12)",
            } as React.CSSProperties
          }
        >
          <AppSidebar
            variant="inset"
            onNavItemClick={(item) => {
              if (item.title === "Projects") setActivePage("projects");
              if (item.title === "Dashboard") setActivePage("study");
            }}
            onNewStudy={() => setActivePage("study")}
          />
          <SidebarInset className="!bg-transparent flex flex-col">
            <SiteHeader title={headerTitle} />

            {activePage === "projects" ? (
              <ProjectsPanel open />
            ) : (
              <>
                <div className="relative flex flex-1 min-h-0 flex-col items-center justify-center gap-4 px-4 pb-4">
                  {panelsOpen && (
                    <>
                      <div
                        className="absolute left-4 top-4 bottom-4 flex flex-col gap-4"
                        style={{ width: "calc((100% - 42rem) / 2 - 2rem)" }}
                      >
                        <div className="flex-1 min-h-0">
                          <GlassSurface
                            width={"100%" as unknown as number}
                            height={"100%" as unknown as number}
                            borderRadius={16}
                            className="overflow-hidden h-full"
                            contentClassName="!p-0 !m-0"
                          >
                            <div className="h-full w-full" />
                          </GlassSurface>
                        </div>
                        <div className="flex-1 min-h-0">
                          <GlassSurface
                            width={"100%" as unknown as number}
                            height={"100%" as unknown as number}
                            borderRadius={16}
                            className="overflow-hidden h-full"
                            contentClassName="!p-0 !m-0"
                          >
                            <div className="h-full w-full" />
                          </GlassSurface>
                        </div>
                      </div>
                      <div
                        className="absolute right-4 top-4 bottom-4 flex flex-col gap-4"
                        style={{ width: "calc((100% - 42rem) / 2 - 2rem)" }}
                      >
                        <div className="flex-1 min-h-0">
                          <GlassSurface
                            width={"100%" as unknown as number}
                            height={"100%" as unknown as number}
                            borderRadius={16}
                            className="overflow-hidden h-full"
                            contentClassName="!p-0 !m-0"
                          >
                            <div className="h-full w-full" />
                          </GlassSurface>
                        </div>
                        <div className="flex-1 min-h-0">
                          <GlassSurface
                            width={"100%" as unknown as number}
                            height={"100%" as unknown as number}
                            borderRadius={16}
                            className="overflow-hidden h-full"
                            contentClassName="!p-0 !m-0"
                          >
                            <div className="h-full w-full" />
                          </GlassSurface>
                        </div>
                      </div>
                    </>
                  )}

                  <div className="flex-1" />
                  <PdbViewerOverlay
                    open={viewerOpen}
                    onClose={() => setViewerOpen(false)}
                  />
                  <ChatbotPanel
                    onSend={() => setHasStarted(true)}
                    messages={messages}
                    onNewMessage={handleNewMessage}
                    isLoading={isLoading}
                    onToggleModelView={() => setModelViewActive((v) => !v)}
                    modelViewActive={modelViewActive}
                    modelViewContent={<EmbeddedModelViewer />}
                  />
                  <div
                    className="transition-[flex-grow] duration-[1400ms] ease-in-out"
                    style={{
                      flexGrow: hasStarted ? 0 : 1,
                      flexShrink: 0,
                      flexBasis: 0,
                    }}
                  />
                </div>
                <button
                  type="button"
                  onClick={() => setPanelsOpen((v) => !v)}
                  className="fixed bottom-16 right-6 z-20 rounded-full bg-black/80 px-4 py-2.5 text-sm font-medium text-white shadow-lg hover:bg-black/90"
                  aria-label="Toggle side panels"
                >
                  {panelsOpen ? "Hide panels" : "Show panels"}
                </button>
                <button
                  type="button"
                  onClick={() => setViewerOpen(true)}
                  className="fixed bottom-6 right-6 z-20 rounded-full bg-black/80 px-4 py-2.5 text-sm font-medium text-white shadow-lg hover:bg-black/90"
                  aria-label="Show protein structure viewer"
                >
                  View structure
                </button>
              </>
            )}
          </SidebarInset>
        </SidebarProvider>
      </div>
    </div>
  );
}
