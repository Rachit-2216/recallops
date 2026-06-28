import {
  BrainCircuit,
  Database,
  GitBranch,
  History,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";

import {
  recallOpsApi,
  type EvidenceItem,
  type RecallResult as RecallResultData,
} from "../../api/recallops";
import { StatusBadge } from "../../components/StatusBadge";
import { ForgetDialog } from "./ForgetDialog";
import { RecallResult } from "./RecallResult";
import { ReferenceList } from "./ReferenceList";

type InspectorTab = "evidence" | "path" | "lifecycle";

type SessionHypothesis = {
  id: string;
  content: string;
  state: string;
};

export function MemoryInspector({
  result,
  evidenceItems = [],
  sessionHypotheses = [],
  onRejectHypothesis,
}: {
  result: RecallResultData;
  evidenceItems?: EvidenceItem[];
  sessionHypotheses?: SessionHypothesis[];
  onRejectHypothesis?: (id: string) => void;
}) {
  const [tab, setTab] = useState<InspectorTab>("evidence");
  const [selectedDataId, setSelectedDataId] = useState(
    result.references[0]?.data_id,
  );
  const [forgetItem, setForgetItem] = useState<EvidenceItem | null>(null);
  const forgetTriggerRef = useRef<HTMLButtonElement>(null);
  const selectedReference =
    result.references.find((item) => item.data_id === selectedDataId) ??
    result.references[0];
  const selectedEvidence = useMemo(
    () =>
      evidenceItems.find(
        (item) => item.data_id === selectedReference?.data_id,
      ),
    [evidenceItems, selectedReference?.data_id],
  );

  const tabs: { id: InspectorTab; label: string; icon: typeof Database }[] = [
    { id: "evidence", label: "Evidence", icon: Database },
    { id: "path", label: "Path", icon: GitBranch },
    { id: "lifecycle", label: "Lifecycle", icon: History },
  ];

  return (
    <>
      <div className="inspector-heading">
        <BrainCircuit size={18} aria-hidden="true" />
        <div>
          <span className="eyebrow">Memory inspector</span>
          <h2>Scoped provenance</h2>
        </div>
        <StatusBadge
          tone={result.verification === "referenced" ? "success" : "warning"}
        >
          {result.verification}
        </StatusBadge>
      </div>
      <RecallResult result={result} />
      {result.references.length > 0 ? (
        <ReferenceList
          onSelect={(dataId) => {
            setSelectedDataId(dataId);
            setTab("evidence");
          }}
          references={result.references}
          selectedDataId={selectedDataId}
        />
      ) : null}
      <div aria-label="Memory inspector views" className="inspector-tabs" role="tablist">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            aria-controls={`inspector-panel-${id}`}
            aria-selected={tab === id}
            id={`inspector-tab-${id}`}
            key={id}
            onClick={() => setTab(id)}
            role="tab"
            type="button"
          >
            <Icon size={13} aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>

      <div
        aria-labelledby={`inspector-tab-${tab}`}
        className="inspector-panel"
        id={`inspector-panel-${tab}`}
        role="tabpanel"
      >
        {tab === "evidence" ? (
          selectedReference ? (
            <details open>
              <summary>{selectedReference.document_name}</summary>
              <dl>
                <div>
                  <dt>Data ID</dt>
                  <dd>{selectedReference.data_id}</dd>
                </div>
                <div>
                  <dt>Chunk ID</dt>
                  <dd>{selectedReference.chunk_id}</dd>
                </div>
              </dl>
              <blockquote>{selectedReference.snippet}</blockquote>
            </details>
          ) : (
            <p className="inspector-note">
              No evidence reference was returned. This answer is unverified.
            </p>
          )
        ) : null}

        {tab === "path" ? (
          result.why_recalled.length ? (
            <ol className="reason-list">
              {result.why_recalled.map((reason, index) => (
                <li key={reason}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  {reason}
                </li>
              ))}
            </ol>
          ) : (
            <p className="inspector-note">No supported recall path exists.</p>
          )
        ) : null}

        {tab === "lifecycle" ? (
          <div className="lifecycle-panel">
            {selectedEvidence ? (
              <>
                <div>
                  <ShieldCheck size={16} aria-hidden="true" />
                  <span>
                    <strong>{selectedEvidence.memory_layer} memory</strong>
                    <small>{selectedEvidence.status}</small>
                  </span>
                </div>
                {selectedEvidence.status === "ready" ? (
                  <button
                    className="danger-link"
                    onClick={() => setForgetItem(selectedEvidence)}
                    ref={forgetTriggerRef}
                    type="button"
                  >
                    Forget memory
                  </button>
                ) : null}
              </>
            ) : (
              <p className="inspector-note">
                Lifecycle metadata is unavailable for this reference.
              </p>
            )}
            {sessionHypotheses.map((candidate) => (
              <div className="hypothesis-lifecycle" key={candidate.id}>
                <span>
                  <strong>Session hypothesis</strong>
                  <small>{candidate.content}</small>
                </span>
                <button
                  className="danger-link"
                  onClick={() => onRejectHypothesis?.(candidate.id)}
                  type="button"
                >
                  <XCircle size={13} aria-hidden="true" />
                  Reject hypothesis · session only
                </button>
              </div>
            ))}
          </div>
        ) : null}
      </div>
      {forgetItem ? (
        <ForgetDialog
          item={forgetItem}
          onClose={() => {
            setForgetItem(null);
            queueMicrotask(() => forgetTriggerRef.current?.focus());
          }}
          onForget={recallOpsApi.forgetEvidence}
        />
      ) : null}
    </>
  );
}
