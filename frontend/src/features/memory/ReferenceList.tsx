import { FileText } from "lucide-react";

import type { RecallResult } from "../../api/recallops";

export function ReferenceList({
  references,
  selectedDataId,
  onSelect,
}: {
  references: RecallResult["references"];
  selectedDataId?: string;
  onSelect: (dataId: string) => void;
}) {
  return (
    <div className="reference-list" aria-label="Recall references">
      {references.map((reference) => (
        <button
          aria-pressed={selectedDataId === reference.data_id}
          className={
            selectedDataId === reference.data_id
              ? "reference-card reference-card--selected"
              : "reference-card"
          }
          key={`${reference.data_id}:${reference.chunk_id}`}
          onClick={() => onSelect(reference.data_id)}
          type="button"
        >
          <FileText size={15} aria-hidden="true" />
          <span>
            <strong>{reference.document_name}</strong>
            <small>{reference.chunk_id}</small>
          </span>
        </button>
      ))}
    </div>
  );
}
