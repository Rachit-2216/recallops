import { CheckCircle2, CircleSlash, Network } from "lucide-react";

import type { RecallResult as RecallResultData } from "../../api/recallops";
import { StatusBadge } from "../../components/StatusBadge";

export function RecallResult({ result }: { result: RecallResultData }) {
  const referenced = result.verification === "referenced";
  return (
    <section className="recall-result" aria-labelledby="recall-answer-title">
      <div className="recall-result__status">
        {referenced ? (
          <CheckCircle2 size={16} aria-hidden="true" />
        ) : (
          <CircleSlash size={16} aria-hidden="true" />
        )}
        <StatusBadge tone={referenced ? "success" : "warning"}>
          {result.verification}
        </StatusBadge>
      </div>
      <span className="eyebrow">Recalled answer</span>
      <h3 className="sr-only" id="recall-answer-title">
        Memory recall answer
      </h3>
      <p>{result.answer ?? "No referenced result was found."}</p>
      <div className="recall-result__provenance">
        <span>
          <Network size={13} aria-hidden="true" /> Source
          <strong>{result.source ?? "none"}</strong>
        </span>
        <span>
          Search type
          <strong>{result.search_type ?? "none"}</strong>
        </span>
      </div>
    </section>
  );
}
