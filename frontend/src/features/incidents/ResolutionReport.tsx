import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  FileCheck2,
  FlaskConical,
  Network,
  ShieldCheck,
} from "lucide-react";
import { useParams } from "react-router-dom";

import { recallOpsApi } from "../../api/recallops";
import { OperationBanner } from "../../components/OperationBanner";
import { StatusBadge } from "../../components/StatusBadge";

export function ResolutionReport() {
  const { incidentId = "" } = useParams();
  const detail = useQuery({
    queryKey: ["incident", incidentId],
    queryFn: ({ signal }) => recallOpsApi.getIncident(incidentId, signal),
    refetchOnMount: "always",
  });
  const proof = useMutation({
    mutationFn: async () => {
      const proofId = `INC-${Date.now().toString().slice(-8)}`;
      await recallOpsApi.createIncident({
        id: proofId,
        title: `Clean-session proof for ${incidentId}`,
        severity: "SEV3",
        service: detail.data?.incident.service ?? "Cloudflare FL1 proxy",
      });
      return recallOpsApi.recallIncident(
        proofId,
        `What verified mitigation fixed ${incidentId}?`,
      );
    },
  });

  if (detail.isPending || (detail.isFetching && !detail.data?.resolution)) {
    return (
      <section className="loading-panel" aria-live="polite">
        <h1>Loading resolution proof</h1>
      </section>
    );
  }
  if (detail.isError || !detail.data.resolution) {
    return (
      <section className="error-panel" role="alert">
        <h1>Verified resolution is unavailable</h1>
        <p>
          {detail.error?.message ??
            "This incident has not completed a confirmed promotion."}
        </p>
      </section>
    );
  }

  const resolution = detail.data.resolution;
  return (
    <section className="resolution-report" aria-labelledby="report-title">
      <header className="page-header">
        <div>
          <span className="eyebrow">Verified learning / immutable proof</span>
          <h1 id="report-title">{incidentId} resolution</h1>
          <p>
            Human-confirmed facts, cited recall traces, and the result of the
            controlled improve operation.
          </p>
        </div>
        <StatusBadge
          tone={
            resolution.promotion_state === "promoted" ? "success" : "warning"
          }
        >
          {resolution.promotion_state}
        </StatusBadge>
      </header>
      <div className="report-grid">
        <article className="verified-facts">
          <div className="report-section-title">
            <FileCheck2 size={18} aria-hidden="true" />
            <h2>Verified facts</h2>
          </div>
          <dl>
            <div>
              <dt>Root cause</dt>
              <dd>{resolution.root_cause}</dd>
            </div>
            <div>
              <dt>Mitigation</dt>
              <dd>{resolution.mitigation}</dd>
            </div>
            <div>
              <dt>Verification</dt>
              <dd>{resolution.verification}</dd>
            </div>
          </dl>
        </article>
        <aside className="promotion-audit">
          <div className="report-section-title">
            <ShieldCheck size={18} aria-hidden="true" />
            <h2>Promotion audit</h2>
          </div>
          <dl>
            <div>
              <dt>Human confirmation</dt>
              <dd>{resolution.confirmed_at ?? "Not recorded"}</dd>
            </div>
            <div>
              <dt>Improve operation</dt>
              <dd>{resolution.promotion_state}</dd>
            </div>
          </dl>
          <h3>Evidence citations</h3>
          <ul>
            {(resolution.trace_ids ?? []).map((traceId) => (
              <li key={traceId}>
                <Network size={13} aria-hidden="true" />
                {traceId}
              </li>
            ))}
          </ul>
        </aside>
      </div>

      <section className="clean-proof" aria-labelledby="clean-proof-title">
        <div>
          <span className="eyebrow">Independent verification</span>
          <h2 id="clean-proof-title">Clean-session retrieval proof</h2>
          <p>
            Create a new incident session and ask for the verified mitigation.
            A valid result must cite permanent memory.
          </p>
        </div>
        <button
          className="primary-action"
          disabled={proof.isPending}
          onClick={() => proof.mutate()}
          type="button"
        >
          <FlaskConical size={16} aria-hidden="true" />
          Prove in clean session
        </button>
        {proof.isPending ? (
          <OperationBanner
            detail="Creating an isolated session and running one scoped recall."
            state="working"
            title="Running clean-session proof"
          />
        ) : null}
        {proof.isError ? (
          <OperationBanner
            detail={proof.error.message}
            state="error"
            title="Clean-session proof failed"
          />
        ) : null}
        {proof.data ? (
          <div className="clean-proof__result" aria-live="polite">
            <CheckCircle2 size={18} aria-hidden="true" />
            <div>
              <strong>{proof.data.verification}</strong>
              <p>{proof.data.answer}</p>
              <small>
                Permanent-memory source:{" "}
                {proof.data.references[0]?.document_name ?? proof.data.source}
              </small>
            </div>
          </div>
        ) : null}
      </section>
    </section>
  );
}
