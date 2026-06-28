import { ArrowDown, FileSearch } from "lucide-react";

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
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const visibleEdges = edges.filter(
    (edge) =>
      edge.evidenceDataId &&
      !excludedEvidenceIds.has(edge.evidenceDataId),
  );
  const primary = visibleEdges.filter((edge) => edge.label !== "obsolete advice");
  const branches = visibleEdges.filter((edge) => edge.label === "obsolete advice");
  const orderedNodes = primary.length
    ? [
        nodeById.get(primary[0].source),
        ...primary.map((edge) => nodeById.get(edge.target)),
      ]
    : [];

  return (
    <section className="memory-graph" aria-label="Evidence-backed memory graph">
      <div className="memory-path">
        {orderedNodes.map((node, index) =>
          node ? (
            <div className="path-segment" key={node.id}>
              <article className={`memory-node memory-node--${node.kind}`}>
                <span>{node.kind}</span>
                <strong>{node.label}</strong>
              </article>
              {primary[index] ? (
                <>
                  <ArrowDown size={16} aria-hidden="true" />
                  <button
                    aria-label={`${primary[index].label}: ${node.label} to ${
                      nodeById.get(primary[index].target)?.label ?? "unknown"
                    }`}
                    className="memory-edge"
                    data-testid={primary[index].id}
                    onClick={() =>
                      onEvidenceSelect(primary[index].evidenceDataId)
                    }
                    type="button"
                  >
                    <span>{primary[index].label}</span>
                    <small>
                      <FileSearch size={11} aria-hidden="true" />
                      evidence {primary[index].evidenceDataId.slice(0, 8)}
                    </small>
                  </button>
                </>
              ) : null}
            </div>
          ) : null,
        )}
      </div>
      {branches.length ? (
        <aside className="graph-branches" aria-label="Superseded relationships">
          <span className="eyebrow">Superseded branch</span>
          {branches.map((edge) => (
            <div key={edge.id}>
              <button
                aria-label={`${edge.label}: ${
                  nodeById.get(edge.source)?.label ?? "unknown"
                } to ${nodeById.get(edge.target)?.label ?? "unknown"}`}
                className="memory-edge memory-edge--stale"
                data-testid={edge.id}
                onClick={() => onEvidenceSelect(edge.evidenceDataId)}
                type="button"
              >
                <span>{edge.label}</span>
                <small>
                  <FileSearch size={11} aria-hidden="true" />
                  evidence {edge.evidenceDataId.slice(0, 8)}
                </small>
              </button>
              <article
                className={`memory-node memory-node--${
                  nodeById.get(edge.target)?.kind ?? "evidence"
                }`}
              >
                <span>{nodeById.get(edge.target)?.kind}</span>
                <strong>{nodeById.get(edge.target)?.label}</strong>
              </article>
            </div>
          ))}
        </aside>
      ) : null}
    </section>
  );
}
