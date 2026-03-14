"use client";

import { useRef, useState, useCallback, useEffect, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { useGLTF, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { Material } from "three";

const DNA_MODEL_URL = "/human_dna.glb";

/** Target size for the model's largest dimension in world units (before camera). */
const MODEL_SIZE = 2.5;
const VIEW_SCALE = 8;
const OPACITY = 0.5;
const DNA_COLOR = 0x606060; // neutral dark grey
const VIEW_TILT_DEG = 30;
const AUTO_ROTATE_SPEED = 3;

/** Stable orbit target so OrbitControls never resets or drifts. */
const ORBIT_TARGET: [number, number, number] = [0, 0, 0];

function clearModelCache() {
  if (
    typeof THREE !== "undefined" &&
    THREE.Cache &&
    typeof THREE.Cache.remove === "function"
  ) {
    THREE.Cache.remove(DNA_MODEL_URL);
  }
}

function DNAModel() {
  const { scene: rawScene } = useGLTF(DNA_MODEL_URL);

  const { clone, center, scale } = useMemo(() => {
    const clone = rawScene.clone(true);
    clone.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(clone);
    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    box.getCenter(center);
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const scale = (MODEL_SIZE / maxDim) * VIEW_SCALE;
    return { clone, center, scale };
  }, [rawScene]);

  useEffect(() => {
    const color = new THREE.Color(DNA_COLOR);
    clone.traverse((node) => {
      const obj = node as unknown as {
        material?: Material | Material[];
        renderOrder?: number;
      };
      if (obj.material) {
        const mats = Array.isArray(obj.material)
          ? obj.material
          : [obj.material];
        mats.forEach((m) => {
          if ("color" in m && m.color instanceof THREE.Color)
            m.color.copy(color);
          m.transparent = true;
          m.opacity = OPACITY;
          m.depthWrite = false; // avoid self-depth fighting on overlapping strands
          m.depthTest = true;
        });
      }
      if (typeof obj.renderOrder === "number") obj.renderOrder = 0;
    });
  }, [clone]);

  return (
    <group scale={scale} position={[0, 0, 0]}>
      <group position={[-center.x, -center.y, -center.z]}>
        <primitive object={clone} />
      </group>
    </group>
  );
}

const buttonStyle: React.CSSProperties = {
  padding: "0.5rem 1rem",
  fontSize: "1rem",
  cursor: "pointer",
  background: "#333",
  color: "#fff",
  border: "1px solid #555",
  borderRadius: "4px",
  marginRight: "0.5rem",
  marginTop: "0.25rem",
};

export type DNAViewerProps = {
  /** World-space point to orbit the camera around. Defaults to [0,0,0] (center of DNA after centering). */
  orbitCenter?: [number, number, number];
};

export default function DNAViewer({ orbitCenter }: DNAViewerProps = {}) {
  const [contextLost, setContextLost] = useState(false);
  const [canvasKey, setCanvasKey] = useState(0);
  const lossCountRef = useRef(0);
  const contextLostRef = useRef(false);
  contextLostRef.current = contextLost;

  const remount = useCallback(() => {
    clearModelCache();
    setCanvasKey((k) => k + 1);
    setContextLost(false);
  }, []);

  const handleContextLost = useCallback((e: Event) => {
    e.preventDefault();
    lossCountRef.current += 1;
    clearModelCache();

    if (lossCountRef.current >= 2) {
      setContextLost(true);
      return;
    }

    requestAnimationFrame(() => {
      setCanvasKey((k) => k + 1);
    });
  }, []);

  const handleContextRestored = useCallback(() => {
    if (contextLostRef.current) {
      lossCountRef.current = 0;
      clearModelCache();
      setCanvasKey((k) => k + 1);
      setContextLost(false);
    }
  }, []);

  const recoverContext = useCallback(() => {
    lossCountRef.current = 0;
    remount();
  }, [remount]);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "transparent",
        position: "relative",
        cursor: "grab",
      }}
    >
      {contextLost && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0,0,0,0.85)",
            color: "#fff",
            fontFamily: "system-ui, sans-serif",
            fontSize: "1.125rem",
            textAlign: "center",
            padding: "2rem",
            zIndex: 10,
          }}
        >
          <div>
            <p style={{ marginBottom: "0.5rem" }}>WebGL context lost.</p>
            <p style={{ opacity: 0.8, marginBottom: "1rem" }}>
              This can happen after sleep, too many tabs, or GPU memory
              pressure.
            </p>
            <button type="button" onClick={recoverContext} style={buttonStyle}>
              Try again
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={buttonStyle}
            >
              Reload page
            </button>
          </div>
        </div>
      )}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: "145%",
            height: "145%",
            transform: `translate(calc(-50%), calc(-50% + 5%)) rotate(-${VIEW_TILT_DEG}deg)`,
          }}
        >
          <Canvas
            key={canvasKey}
            style={{ width: "100%", height: "100%" }}
            camera={{ position: [0, 0, 12], fov: 50 }}
            gl={{
              alpha: true,
              antialias: true,
              powerPreference: "default",
              failIfMajorPerformanceCaveat: false,
              preserveDrawingBuffer: false,
            }}
            onCreated={({ gl, scene }) => {
              gl.setClearColor(0x000000, 0);
              scene.background = null;
              const dpr = Math.min(window.devicePixelRatio, 2);
              gl.setPixelRatio(dpr);

              const canvas = gl.domElement;
              canvas.addEventListener("webglcontextlost", handleContextLost);
              canvas.addEventListener(
                "webglcontextrestored",
                handleContextRestored,
              );
            }}
          >
            <ambientLight intensity={2} />
            <directionalLight position={[8, 8, 6]} intensity={3} />
            <directionalLight position={[-8, 6, 4]} intensity={2} />
            <directionalLight position={[0, -10, 2]} intensity={1.5} />
            <pointLight position={[0, 0, 8]} intensity={2} />
            <OrbitControls
              makeDefault
              target={orbitCenter ?? ORBIT_TARGET}
              autoRotate
              autoRotateSpeed={AUTO_ROTATE_SPEED}
              enablePan
              enableZoom={false}
              minPolarAngle={Math.PI / 2}
              maxPolarAngle={Math.PI / 2}
            />
            <DNAModel />
          </Canvas>
        </div>
      </div>
    </div>
  );
}
