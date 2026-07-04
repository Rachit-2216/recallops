import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";

import {
  CONSTELLATION_EDGES,
  CONSTELLATION_NODES,
} from "./constellationData";

function CausalLine({
  from,
  to,
}: {
  from: readonly [number, number, number];
  to: readonly [number, number, number];
}) {
  const positions = useMemo(
    () => new Float32Array([...from, ...to]),
    [from, to],
  );

  return (
    <line>
      <bufferGeometry>
        <bufferAttribute
          args={[positions, 3]}
          attach="attributes-position"
        />
      </bufferGeometry>
      <lineBasicMaterial
        color="#68f7e2"
        opacity={0.32}
        transparent
      />
    </line>
  );
}

function IncidentCore() {
  const core = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (!core.current) return;
    core.current.rotation.x += delta * 0.09;
    core.current.rotation.y -= delta * 0.13;
    const pulse = 1 + Math.sin(state.clock.elapsedTime * 1.4) * 0.045;
    core.current.scale.setScalar(pulse);
  });

  return (
    <group>
      <mesh ref={core}>
        <icosahedronGeometry args={[0.92, 1]} />
        <meshPhysicalMaterial
          color="#0d2826"
          emissive="#68f7e2"
          emissiveIntensity={0.36}
          metalness={0.72}
          roughness={0.22}
          transparent
          opacity={0.94}
          wireframe
        />
      </mesh>
      <mesh rotation={[Math.PI / 2.7, 0, 0]}>
        <torusGeometry args={[1.32, 0.012, 8, 120]} />
        <meshBasicMaterial color="#68f7e2" opacity={0.38} transparent />
      </mesh>
      <mesh rotation={[0.6, 0.35, 0.2]}>
        <torusGeometry args={[1.7, 0.008, 8, 120]} />
        <meshBasicMaterial color="#ffb657" opacity={0.2} transparent />
      </mesh>
    </group>
  );
}

function Scene({
  onReady,
  selectedId,
}: {
  onReady: () => void;
  selectedId: string;
}) {
  const group = useRef<THREE.Group>(null);
  const reportedReady = useRef(false);
  const dragStart = useRef<{ x: number; y: number } | null>(null);
  const targetRotation = useRef({ x: 0.08, y: -0.15 });
  const [dragging, setDragging] = useState(false);
  const nodeById = new Map(CONSTELLATION_NODES.map((node) => [node.id, node]));

  useFrame((state, delta) => {
    if (!reportedReady.current) {
      reportedReady.current = true;
      onReady();
    }
    if (!group.current) return;
    if (!dragging) {
      targetRotation.current.y += delta * 0.045;
      targetRotation.current.x = state.pointer.y * 0.1;
    }
    group.current.rotation.x = THREE.MathUtils.lerp(
      group.current.rotation.x,
      targetRotation.current.x,
      0.045,
    );
    group.current.rotation.y = THREE.MathUtils.lerp(
      group.current.rotation.y,
      targetRotation.current.y + state.pointer.x * 0.14,
      0.045,
    );
  });

  return (
    <group
      onPointerDown={(event) => {
        event.stopPropagation();
        dragStart.current = { x: event.clientX, y: event.clientY };
        setDragging(true);
      }}
      onPointerMove={(event) => {
        if (!dragStart.current) return;
        targetRotation.current.y +=
          (event.clientX - dragStart.current.x) * 0.004;
        targetRotation.current.x +=
          (event.clientY - dragStart.current.y) * 0.004;
        dragStart.current = { x: event.clientX, y: event.clientY };
      }}
      onPointerUp={() => {
        dragStart.current = null;
        setDragging(false);
      }}
      ref={group}
    >
      <IncidentCore />
      {CONSTELLATION_EDGES.map(([sourceId, targetId]) => {
        const source = nodeById.get(sourceId);
        const target = nodeById.get(targetId);
        return source && target ? (
          <CausalLine
            from={source.position}
            key={`${sourceId}-${targetId}`}
            to={target.position}
          />
        ) : null;
      })}
      {CONSTELLATION_NODES.map((node, index) => {
        const selected = node.id === selectedId;
        return (
          <mesh
            key={node.id}
            position={[...node.position]}
            rotation={[index * 0.24, index * 0.33, index * 0.12]}
            scale={selected ? 1.34 : 1}
          >
            <octahedronGeometry args={[selected ? 0.31 : 0.24, 0]} />
            <meshPhysicalMaterial
              color={node.color}
              emissive={node.color}
              emissiveIntensity={selected ? 0.62 : 0.18}
              metalness={0.7}
              roughness={0.24}
              wireframe={!selected}
            />
          </mesh>
        );
      })}
    </group>
  );
}

export function MemoryConstellationCanvas({
  frameLoop,
  onReady,
  selectedId,
}: {
  frameLoop: "always" | "demand";
  onReady: () => void;
  selectedId: string;
}) {
  return (
    <Canvas
      aria-hidden="true"
      camera={{ fov: 42, position: [0, 0, 8] }}
      className="constellation-canvas"
      dpr={[1, 1.5]}
      frameloop={frameLoop}
      gl={{
        alpha: true,
        antialias: true,
        powerPreference: "high-performance",
      }}
    >
      <ambientLight intensity={0.5} />
      <pointLight color="#68f7e2" intensity={18} position={[2, 4, 5]} />
      <pointLight color="#ffb657" intensity={10} position={[-5, -2, 3]} />
      <Scene onReady={onReady} selectedId={selectedId} />
    </Canvas>
  );
}
