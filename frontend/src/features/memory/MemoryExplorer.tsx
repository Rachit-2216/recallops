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
  { id: "deploy", label: "deploy-418", kind: "deployment" },
  { id: "ttl", label: "session TTL configuration", kind: "dependency" },
  { id: "redis", label: "Redis sessions", kind: "dependency" },
  { id: "misses", label: "session misses", kind: "symptom" },
  { id: "prior", label: "INC-1842", kind: "incident" },
  { id: "flush", label: "flush all Redis cache", kind: "resolution" },
];

const SEEDED_MEMORY_EDGES: MemoryEdge[] = [
  {
    id: "edge-changed",
    source: "deploy",
    target: "ttl",
    label: "changed",
    evidenceDataId: "a0f3df9f-bfa2-5826-a5dd-1a39e1442327",
  },
  {
    id: "edge-affects",
    source: "ttl",
    target: "redis",
    label: "affects",
    evidenceDataId: "e720a10a-eea4-5cca-b747-faac6b1ad7c8",
  },
  {
    id: "edge-caused",
    source: "redis",
    target: "misses",
    label: "caused",
    evidenceDataId: "3cc911c6-cdfc-5582-b10c-4107bfa6d4d0",
  },
  {
    id: "edge-resembles",
    source: "misses",
    target: "prior",
    label: "resembles",
    evidenceDataId: "e720a10a-eea4-5cca-b747-faac6b1ad7c8",
  },
  {
    id: "edge-stale",
    source: "redis",
    target: "flush",
    label: "obsolete advice",
    evidenceDataId: "a8307fb4-8acb-5342-a97f-56548e38fc97",
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
            <span>INC-2048 relationship trace</span>
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
