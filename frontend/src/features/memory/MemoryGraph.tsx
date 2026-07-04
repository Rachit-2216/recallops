import {
  Background,
  BaseEdge,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  getSmoothStepPath,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { FileSearch } from "lucide-react";
import { useMemo } from "react";

export type MemoryNodeKind =
  | "incident"
  | "service"
  | "deployment"
  | "dependency"
  | "symptom"
  | "evidence"
  | "resolution";

export type MemoryNode = {
  id: string;
  label: string;
  kind: MemoryNodeKind;
};

export type MemoryEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  evidenceDataId: string;
};

type FlowNodeData = {
  label: string;
  kind: MemoryNodeKind;
};

type FlowEdgeData = {
  evidenceDataId: string;
  label: string;
  onEvidenceSelect: (dataId: string) => void;
  stale: boolean;
};

type RecallFlowNode = Node<FlowNodeData, "memoryNode">;
type RecallFlowEdge = Edge<FlowEdgeData, "evidenceEdge">;

const NODE_POSITIONS = [
  { x: 40, y: 170 },
  { x: 330, y: 70 },
  { x: 620, y: 220 },
  { x: 910, y: 70 },
  { x: 1200, y: 220 },
  { x: 330, y: 430 },
];

function MemoryNodeCard({ data }: NodeProps<RecallFlowNode>) {
  return (
    <article className={`flow-memory-node flow-memory-node--${data.kind}`}>
      <Handle
        className="flow-memory-handle"
        position={Position.Left}
        type="target"
      />
      <span>{data.kind}</span>
      <strong>{data.label}</strong>
      <Handle
        className="flow-memory-handle"
        position={Position.Right}
        type="source"
      />
    </article>
  );
}

function EvidenceEdge({
  data,
  id,
  markerEnd,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
}: EdgeProps<RecallFlowEdge>) {
  const [edgePath] = getSmoothStepPath({
    borderRadius: 24,
    offset: 24,
    sourcePosition,
    sourceX,
    sourceY,
    targetPosition,
    targetX,
    targetY,
  });

  return (
    <BaseEdge
      className={data?.stale ? "flow-edge flow-edge--stale" : "flow-edge"}
      id={id}
      markerEnd={markerEnd}
      path={edgePath}
    />
  );
}

const nodeTypes = { memoryNode: MemoryNodeCard };
const edgeTypes = { evidenceEdge: EvidenceEdge };

export function MemoryGraph({
  nodes,
  edges,
  excludedEvidenceIds = new Set<string>(),
  onEvidenceSelect,
}: {
  nodes: MemoryNode[];
  edges: MemoryEdge[];
  excludedEvidenceIds?: Set<string>;
  onEvidenceSelect: (dataId: string) => void;
}) {
  const visibleEdges = useMemo(
    () =>
      edges.filter(
        (edge) =>
          edge.evidenceDataId &&
          !excludedEvidenceIds.has(edge.evidenceDataId),
      ),
    [edges, excludedEvidenceIds],
  );
  const connectedNodeIds = useMemo(
    () =>
      new Set(visibleEdges.flatMap((edge) => [edge.source, edge.target])),
    [visibleEdges],
  );
  const flowNodes = useMemo<RecallFlowNode[]>(
    () =>
      nodes
        .filter((node) => connectedNodeIds.has(node.id))
        .map((node, index) => ({
          id: node.id,
          type: "memoryNode",
          data: { kind: node.kind, label: node.label },
          initialHeight: 84,
          initialWidth: 218,
          position: NODE_POSITIONS[index] ?? {
            x: 80 + index * 240,
            y: 160,
          },
        })),
    [connectedNodeIds, nodes],
  );
  const flowEdges = useMemo<RecallFlowEdge[]>(
    () =>
      visibleEdges.map((edge) => ({
        id: edge.id,
        type: "evidenceEdge",
        source: edge.source,
        target: edge.target,
        markerEnd: {
          color: edge.label.includes("unsafe") ? "#ff756d" : "#68f7e2",
          height: 15,
          type: MarkerType.ArrowClosed,
          width: 15,
        },
        data: {
          evidenceDataId: edge.evidenceDataId,
          label: edge.label,
          onEvidenceSelect,
          stale:
            edge.label.includes("unsafe") ||
            edge.label.includes("obsolete"),
        },
      })),
    [onEvidenceSelect, visibleEdges],
  );

  return (
    <section className="memory-graph" aria-label="Evidence-backed memory graph">
      <div className="memory-flow-canvas">
        <ReactFlow
          colorMode="dark"
          edgeTypes={edgeTypes}
          edges={flowEdges}
          fitView
          fitViewOptions={{ padding: 0.16 }}
          maxZoom={1.55}
          minZoom={0.48}
          nodeTypes={nodeTypes}
          nodes={flowNodes}
          nodesConnectable={false}
          nodesDraggable={false}
          panOnScroll
          proOptions={{ hideAttribution: true }}
          zoomOnDoubleClick={false}
        >
          <Background color="rgba(104,247,226,.12)" gap={28} size={1} />
          <Controls
            fitViewOptions={{ padding: 0.16 }}
            position="bottom-right"
            showInteractive={false}
          />
        </ReactFlow>
        <div className="flow-edge-controls">
          {visibleEdges.map((edge, index) => {
            const stale =
              edge.label.includes("unsafe") ||
              edge.label.includes("obsolete");
            return (
              <button
                aria-label={`Inspect relationship ${edge.label}`}
                className={`flow-edge-label${
                  stale ? " flow-edge-label--stale" : ""
                }`}
                data-testid={edge.id}
                key={edge.id}
                onClick={() => onEvidenceSelect(edge.evidenceDataId)}
                style={{ "--edge-index": index } as React.CSSProperties}
                type="button"
              >
                <span>{edge.label}</span>
                <small>
                  <FileSearch size={10} aria-hidden="true" />
                  {edge.evidenceDataId.slice(0, 8)}
                </small>
              </button>
            );
          })}
        </div>
      </div>

      <ol
        aria-label="Evidence-backed relationship list"
        className="relationship-index"
      >
        {visibleEdges.map((edge, index) => {
          const source = nodes.find((node) => node.id === edge.source);
          const target = nodes.find((node) => node.id === edge.target);
          return (
            <li key={edge.id}>
              <button
                aria-label={`Inspect ${edge.label}: ${source?.label ?? edge.source} to ${
                  target?.label ?? edge.target
                }`}
                onClick={() => onEvidenceSelect(edge.evidenceDataId)}
                type="button"
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                <FileSearch size={13} aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
