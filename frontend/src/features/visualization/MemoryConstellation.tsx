import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ConstellationFallback } from "./ConstellationFallback";
import {
  CONSTELLATION_NODES,
  type ConstellationNode,
} from "./constellationData";
import {
  selectConstellationMode,
  selectFrameLoop,
  selectSceneStatus,
} from "./constellationPolicy";

const MemoryConstellationCanvas = lazy(() =>
  import("./MemoryConstellationCanvas").then((module) => ({
    default: module.MemoryConstellationCanvas,
  })),
);

function hasWebGL() {
  return (
    typeof window !== "undefined" &&
    typeof window.WebGLRenderingContext !== "undefined"
  );
}

function useConstellationMode() {
  const [mode, setMode] = useState<"fallback" | "webgl">("fallback");

  useEffect(() => {
    if (typeof window.matchMedia !== "function") {
      setMode("fallback");
      return;
    }
    const compact = window.matchMedia("(max-width: 760px)");
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () =>
      setMode(
        selectConstellationMode({
          compactViewport: compact.matches,
          reducedMotion: reduced.matches,
          webglAvailable: hasWebGL(),
        }),
      );

    update();
    compact.addEventListener("change", update);
    reduced.addEventListener("change", update);
    return () => {
      compact.removeEventListener("change", update);
      reduced.removeEventListener("change", update);
    };
  }, []);

  return mode;
}

function NodeControls({
  nodes,
  onSelect,
  selectedId,
}: {
  nodes: ConstellationNode[];
  onSelect: (nodeId: string) => void;
  selectedId: string;
}) {
  return (
    <div className="constellation-controls" aria-label="Constellation evidence">
      {nodes.map((node, index) => (
        <button
          aria-label={`Inspect evidence node: ${node.label}`}
          aria-pressed={node.id === selectedId}
          key={node.id}
          onClick={() => onSelect(node.id)}
          style={{ "--node-color": node.color } as React.CSSProperties}
          type="button"
        >
          <span>{String(index + 1).padStart(2, "0")}</span>
          {node.label}
        </button>
      ))}
    </div>
  );
}

export function MemoryConstellation() {
  const mode = useConstellationMode();
  const shellRef = useRef<HTMLElement>(null);
  const [inViewport, setInViewport] = useState(true);
  const [documentVisible, setDocumentVisible] = useState(
    () => typeof document === "undefined" || document.visibilityState !== "hidden",
  );
  const [sceneReady, setSceneReady] = useState(false);
  const [selectedId, setSelectedId] = useState(CONSTELLATION_NODES[0].id);
  const selected = useMemo(
    () =>
      CONSTELLATION_NODES.find((node) => node.id === selectedId) ??
      CONSTELLATION_NODES[0],
    [selectedId],
  );
  const frameLoop = selectFrameLoop({ documentVisible, inViewport });
  const sceneStatus = selectSceneStatus(mode, sceneReady);

  useEffect(() => {
    if (mode === "fallback") setSceneReady(false);
  }, [mode]);

  useEffect(() => {
    const handleVisibility = () =>
      setDocumentVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", handleVisibility);

    if (typeof IntersectionObserver !== "function" || !shellRef.current) {
      return () =>
        document.removeEventListener("visibilitychange", handleVisibility);
    }
    const observer = new IntersectionObserver(
      ([entry]) => setInViewport(entry.isIntersecting),
      { rootMargin: "120px" },
    );
    observer.observe(shellRef.current);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, []);

  return (
    <section
      aria-label="Interactive incident memory"
      className="memory-constellation-shell"
      ref={shellRef}
    >
      <div className="constellation-stage">
        <div className="constellation-stage__label">
          <span>INCIDENT CORE / LIVE MODEL</span>
          <strong>{sceneStatus}</strong>
        </div>
        {mode === "webgl" ? (
          <>
            {!sceneReady ? (
              <ConstellationFallback
                nodes={CONSTELLATION_NODES}
                selectedId={selectedId}
              />
            ) : null}
            <Suspense fallback={null}>
              <MemoryConstellationCanvas
                frameLoop={frameLoop}
                onReady={() => setSceneReady(true)}
                selectedId={selectedId}
              />
            </Suspense>
          </>
        ) : (
          <ConstellationFallback
            nodes={CONSTELLATION_NODES}
            selectedId={selectedId}
          />
        )}
        <div className="constellation-reticle" aria-hidden="true" />
      </div>

      <NodeControls
        nodes={CONSTELLATION_NODES}
        onSelect={setSelectedId}
        selectedId={selectedId}
      />

      <div className="constellation-readout" aria-live="polite">
        <span style={{ background: selected.color }} />
        <div>
          <small>{selected.kind}</small>
          <strong>{selected.label}</strong>
          <p>{selected.detail}</p>
        </div>
      </div>
    </section>
  );
}
