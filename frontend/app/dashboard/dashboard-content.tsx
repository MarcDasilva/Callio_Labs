"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { AppSidebar } from "@/components/app-sidebar";
import { ChatbotPanel } from "@/components/chatbot-panel";
import { CallioLabsSplash } from "@/components/callio-labs-splash";
import GlassSurface from "@/components/GlassSurface";
import { SiteHeader } from "@/components/site-header";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
const Dither = dynamic(() => import("@/components/Dither"), { ssr: false });
const PdbViewerOverlay = dynamic(
  () => import("@/components/pdb-viewer-overlay").then((m) => ({ default: m.PdbViewerOverlay })),
  { ssr: false }
);

export function DashboardContent() {
  const [hasStarted, setHasStarted] = useState(false);
  const [viewerOpen, setViewerOpen] = useState(false);

  return (
    <div className="relative min-h-screen w-full">
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
          <AppSidebar variant="inset" />
          <SidebarInset className="!bg-transparent flex flex-col">
            <SiteHeader />
            <div className="flex flex-1 min-h-0 flex-col items-center gap-8 px-4 pb-6">
              <div className="flex-1" />
              <PdbViewerOverlay open={viewerOpen} onClose={() => setViewerOpen(false)} />
              <aside className="w-full max-w-2xl px-4">
                <GlassSurface
                  width="100%"
                  height="fit-content"
                  borderRadius={16}
                  className="overflow-hidden"
                  contentClassName="!flex !flex-col !items-stretch !justify-center !p-0 !gap-0"
                >
                  <div className="h-24" />
                </GlassSurface>
              </aside>
              <ChatbotPanel onSend={() => setHasStarted(true)} />
              <div
                className="transition-[flex-grow] duration-[1400ms] ease-in-out"
                style={{
                  flexGrow: hasStarted ? 0 : 1,
                  flexShrink: 0,
                  flexBasis: 0,
                }}
              />
            </div>
          </SidebarInset>
        </SidebarProvider>
      </div>
      <button
        type="button"
        onClick={() => setViewerOpen(true)}
        className="fixed bottom-6 right-6 z-20 rounded-full bg-black/80 px-4 py-2.5 text-sm font-medium text-white shadow-lg hover:bg-black/90"
        aria-label="Show protein structure viewer"
      >
        View structure
      </button>
    </div>
  );
}
