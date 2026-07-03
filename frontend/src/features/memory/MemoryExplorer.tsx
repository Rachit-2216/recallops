import { useQuery } from "@tanstack/react-query";
import { Network } from "lucide-react";
import { useState } from "react";

import { recallOpsApi } from "../../api/recallops";
import { StatusBadge } from "../../components/StatusBadge";
import { EvidenceCard } from "../evidence/EvidenceCard";
import {
  MemoryGraph,
  type MemoryEdge,
  type MemoryNode,
} from "./MemoryGraph";

const SEEDED_MEMORY_NODES: MemoryNode[] = [
  { id: "change", label: "global WAF config", kind: "deployment" },
  { id: "execute", label: "FL1 execute object", kind: "dependency" },
  { id: "nil", label: "nil dereference", kind: "dependency" },
  { id: "errors", label: "HTTP 500 errors", kind: "symptom" },
  { id: "prior", label: "November 18 outage", kind: "incident" },
  {
    id: "unsafe",
    label: "global killswitch is always safe",
    kind: "resolution",
  },
];

const SEEDED_MEMORY_EDGES: MemoryEdge[] = [
  {
    id: "edge-removed",
    source: "change",
    target: "execute",
    label: "removed",
    evidenceDataId: "14a64a50-0d7f-59c2-91cc-f2c3f5e66180",
  },
  {
    id: "edge-triggered",
    source: "execute",
    target: "nil",
    label: "triggered",
    evidenceDataId: "bb5452e4-ad31-5b98-b703-ac30dbd8592f",
  },
  {
    id: "edge-caused",
    source: "nil",
    target: "errors",
    label: "caused",
    evidenceDataId: "61cabe3d-4609-5940-9234-4818ab2cff32",
  },
  {
    id: "edge-resembles",
    source: "errors",
    target: "prior",
    label: "shares blast-radius risk",
    evidenceDataId: "e106b3e1-46de-549f-a229-e451b34e7205",
  },
  {
    id: "edge-stale",
    source: "change",
    target: "unsafe",
    label: "unsafe assumption",
    evidenceDataId: "bc1e5f47-cce5-5865-b7db-4a8cf68d5680",
  },
];

export function MemoryExplorer() {
  const [selectedDataId, setSelectedDataId] = useState<string>();
  const evidence = useQuery({
    queryKey: ["evidence"],
    queryFn: ({ signal }) => recallOpsApi.listEvidence(signal),
  });
  const forgotten = new Set(
    evidence.data?.items
      .filter((item) => item.status === "forgotten")
      .map((item) => item.data_id) ?? [],
  );
  const selected = evidence.data?.items.find(
    (item) => item.data_id === selectedDataId,
  );

  return (
    <section className="memory-explorer" aria-labelledby="memory-graph-title">
      <header className="page-header">
        <div>
          <span className="eyebrow">Graph memory / stored relationships</span>
          <h1 id="memory-graph-title">Causal memory path</h1>
          <p>
            Every connector below resolves to stored evidence. Forgotten
            evidence removes only its connector; shared entities remain.
          </p>
        </div>
        <StatusBadge tone="graph">5 evidence-backed edges</StatusBadge>
      </header>
      <div className="explorer-layout">
        <div className="graph-stage">
          <div className="graph-stage__header">
            <Network size={16} aria-hidden="true" />
            <span>CF-OUTAGE-2025-12-05 relationship trace</span>
            <strong>NO INFERRED EDGES</strong>
          </div>
          <MemoryGraph
            edges={SEEDED_MEMORY_EDGES}
            excludedEvidenceIds={forgotten}
            nodes={SEEDED_MEMORY_NODES}
            onEvidenceSelect={setSelectedDataId}
          />
        </div>
        <aside className="graph-evidence" aria-label="Selected graph evidence">
          {selected ? (
            <EvidenceCard item={selected} />
          ) : (
            <div className="inspector-empty">
              <p>
                Select a relationship label to inspect the permanent evidence
                data ID that supports it.
              </p>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}
