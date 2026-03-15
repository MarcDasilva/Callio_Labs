"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import GlassSurface from "@/components/GlassSurface";

const RENDERED_FOLD_FILES = [
  { path: "/rendered_folds/1HTM_icn3d.pdb", label: "1HTM" },
  { path: "/rendered_folds/1HGJ_icn3d.pdb", label: "1HGJ" },
  { path: "/rendered_folds/9H6U_icn3d.pdb", label: "9H6U" },
] as const;

const VIEWER_HEIGHT = 580;

type PdbViewerOverlayProps = {
  open: boolean;
  onClose: () => void;
};

export function PdbViewerOverlay({ open, onClose }: PdbViewerOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fadeIn, setFadeIn] = useState(false);
  const [modelIndex, setModelIndex] = useState(0);

  const destroyViewer = useCallback(() => {
    const v = viewerRef.current as { clear?: () => void } | null;
    if (v && typeof v.clear === "function") v.clear();
    viewerRef.current = null;
    if (containerRef.current) containerRef.current.innerHTML = "";
  }, []);

  const loadModel = useCallback(
    async (index: number) => {
      if (!containerRef.current || !open) return;
      destroyViewer();
      setError(null);
      setLoading(true);
      try {
        const el = containerRef.current;
        const rect = el.getBoundingClientRect();
        el.style.width = `${rect.width}px`;
        el.style.height = `${rect.height}px`;

        const $3Dmol = await import("3dmol");
        const viewer = $3Dmol.createViewer(el, {
          backgroundColor: "white",
        });
        viewerRef.current = viewer;

        const res = await fetch(RENDERED_FOLD_FILES[index].path);
        if (!res.ok) throw new Error(`Failed to load model: ${res.status}`);
        const pdbData = await res.text();

        viewer.addModel(pdbData, "pdb");
        viewer.setStyle(
          {},
          { cartoon: { color: "spectrum" }, stick: { colorscheme: "default" } },
        );
        viewer.setBackgroundColor("white", 0);
        viewer.zoomTo();
        viewer.zoom(1.3);
        viewer.rotate(Math.random() * 360, "x");
        viewer.rotate(Math.random() * 360, "y");
        viewer.rotate(Math.random() * 360, "z");
        viewer.resize();
        viewer.render();
        viewer.spin("z", 0.2);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load viewer");
      } finally {
        setLoading(false);
      }
    },
    [open, destroyViewer],
  );

  const switchModel = useCallback(() => {
    const next = (modelIndex + 1) % RENDERED_FOLD_FILES.length;
    setModelIndex(next);
    setTimeout(() => loadModel(next), 80);
  }, [modelIndex, loadModel]);

  useEffect(() => {
    if (!open) {
      destroyViewer();
      return;
    }
    setFadeIn(false);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => setFadeIn(true));
    });
    const id = setTimeout(() => loadModel(modelIndex), 80);
    return () => {
      clearTimeout(id);
      destroyViewer();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="relative w-full max-w-2xl px-4 transition-opacity duration-500 ease-out"
      style={{ opacity: fadeIn ? 1 : 0 }}
    >
      <GlassSurface
        width="100%"
        height={VIEWER_HEIGHT}
        borderRadius={16}
        brightness={70}
        opacity={0.98}
        blur={16}
        backgroundOpacity={0.35}
        className="overflow-hidden"
        contentClassName="!p-0 !m-0"
      >
        <div className="absolute right-3 top-2 z-10 flex items-center gap-1.5">
          <span className="rounded-full bg-black/10 px-2.5 py-1 text-xs text-black/50">
            {RENDERED_FOLD_FILES[modelIndex].label}
          </span>
          <button
            type="button"
            onClick={switchModel}
            className="rounded-full bg-black/10 px-2.5 py-1 text-xs text-black/60 hover:bg-black/20 hover:text-black/80"
            aria-label="Switch model"
          >
            Next
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-black/10 px-2.5 py-1 text-xs text-black/60 hover:bg-black/20 hover:text-black/80"
            aria-label="Close viewer"
          >
            ✕
          </button>
        </div>
        {loading && (
          <div className="absolute inset-0 z-5 flex items-center justify-center text-sm text-black/50">
            Loading model…
          </div>
        )}
        {error && (
          <div className="absolute inset-0 z-5 flex items-center justify-center text-sm text-red-500/80">
            {error}
          </div>
        )}
        <div
          ref={containerRef}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
          }}
        />
      </GlassSurface>
    </div>
  );
}
