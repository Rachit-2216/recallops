import { useQuery } from "@tanstack/react-query";
import { Database, Upload } from "lucide-react";

import {
  recallOpsApi,
  type EvidenceItem as ApiEvidenceItem,
} from "../../api/recallops";
import { StatusBadge } from "../../components/StatusBadge";
import { EvidenceCard } from "./EvidenceCard";

export type EvidenceItem = ApiEvidenceItem;

type EvidenceLibraryViewProps = {
  items: EvidenceItem[];
  publicDemo?: boolean;
};

export function EvidenceLibraryView({
  items,
  publicDemo = import.meta.env.VITE_PUBLIC_DEMO === "true",
}: EvidenceLibraryViewProps) {
  const activeCount = items.filter(
    (item) => item.status !== "forgotten",
  ).length;
  return (
    <section className="evidence-library" aria-labelledby="evidence-title">
      <header className="page-header">
        <div>
          <span className="eyebrow">Permanent memory / evidence registry</span>
          <h1 id="evidence-title">Evidence library</h1>
          <p>
            Inspect the stable records eligible for cross-incident retrieval.
            Audit-only records remain visible but cannot influence recall.
          </p>
        </div>
        <div className="page-header__actions">
          <StatusBadge tone="graph">{activeCount} active</StatusBadge>
          {!publicDemo ? (
            <button className="secondary-action" type="button">
              <Upload size={16} aria-hidden="true" /> Upload evidence
            </button>
          ) : null}
        </div>
      </header>
      <div className="library-summary">
        <Database size={17} aria-hidden="true" />
        <span>recallops_evidence_v1</span>
        <strong>{items.length} audited records</strong>
      </div>
      <div className="evidence-grid">
        {items.map((item) => (
          <EvidenceCard item={item} key={item.data_id} />
        ))}
      </div>
    </section>
  );
}

export function EvidenceLibrary() {
  const evidence = useQuery({
    queryKey: ["evidence"],
    queryFn: ({ signal }) => recallOpsApi.listEvidence(signal),
  });

  if (evidence.isPending) {
    return (
      <section className="loading-panel" aria-live="polite">
        <span className="eyebrow">Evidence registry</span>
        <h1>Reading local audit index</h1>
        <p>No external memory operation is running.</p>
      </section>
    );
  }
  if (evidence.isError) {
    return (
      <section className="error-panel" role="alert">
        <span className="eyebrow">Evidence registry unavailable</span>
        <h1>Permanent memory could not be listed</h1>
        <p>{evidence.error.message}</p>
      </section>
    );
  }
  return <EvidenceLibraryView items={evidence.data.items} />;
}
