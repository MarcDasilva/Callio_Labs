"use client";

import dynamic from "next/dynamic";
import { AppSidebar } from "@/components/app-sidebar";
import { ChatbotPanel } from "@/components/chatbot-panel";
import { CallioLabsSplash } from "@/components/callio-labs-splash";
import { SiteHeader } from "@/components/site-header";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";

const Dither = dynamic(() => import("@/components/Dither"), { ssr: false });

export function DashboardContent() {
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
            <div className="flex flex-1 min-h-0 items-center justify-center p-4">
              <ChatbotPanel />
            </div>
          </SidebarInset>
        </SidebarProvider>
      </div>
    </div>
  );
}
