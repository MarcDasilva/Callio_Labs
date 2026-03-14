"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const Dither = dynamic(() => import("@/components/Dither"), { ssr: false });
const DNAViewer = dynamic(() => import("@/components/dna-viewer"), {
  ssr: false,
});

export default function Page() {
  const [splashDone, setSplashDone] = useState(false);

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      {/* Content loads first underneath */}
      <div className="absolute inset-0 z-0">
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
      <div className="absolute inset-0 z-0">
        <DNAViewer />
      </div>
      {/* Bottom-left branding: callio labs + tagline */}
      <div
        className="absolute bottom-0 left-0 z-10 pb-24 md:pb-32 lg:pb-40 pl-12 md:pl-16 lg:pl-20 flex flex-col gap-0"
      >
        <span
          className="font-semibold text-foreground leading-none text-6xl md:text-7xl lg:text-8xl"
          style={{ fontFamily: '"Callio", sans-serif' }}
        >
          callio labs
        </span>
        <span
          className="text-foreground text-xl md:text-2xl lg:text-3xl opacity-70 leading-none -mt-1 md:-mt-1.5 lg:-mt-2"
          style={{ fontFamily: '"Synonym", serif' }}
        >
          agentic genome research
        </span>
      </div>
      {/* White overlay on top — fades out after 2s; content is already loaded underneath */}
      <div
        className="fixed inset-0 z-[9999] bg-white animate-white-splash"
        onAnimationEnd={() => setSplashDone(true)}
        style={{ pointerEvents: splashDone ? "none" : "auto" }}
        aria-hidden
      />
    </div>
  );
}
