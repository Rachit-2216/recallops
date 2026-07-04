import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, RotateCcw, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  recallOpsApi,
  type ResolutionRequest,
  type ResolutionResponse,
} from "../../api/recallops";
import { OperationBanner } from "../../components/OperationBanner";
import { StatusBadge } from "../../components/StatusBadge";

type ResolutionResult = Pick<
  ResolutionResponse,
  "promotion_state" | "confirmed_at"
>;

export function ResolutionPanel({
  incidentId,
  traceIds,
  onResolve = (body) => recallOpsApi.resolveIncident(incidentId, body),
}: {
  incidentId: string;
  traceIds: string[];
  onResolve?: (body: ResolutionRequest) => Promise<ResolutionResult>;
}) {
  const [rootCause, setRootCause] = useState("");
  const [mitigation, setMitigation] = useState("");
  const [verification, setVerification] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const queryClient = useQueryClient();
  const promotion = useMutation({
    mutationFn: onResolve,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["incident", incidentId] }),
  });
  const valid =
    rootCause.trim() &&
    mitigation.trim() &&
    verification.trim() &&
    traceIds.length > 0 &&
    confirmed;
  const state = promotion.isPending
    ? "promotion_pending"
    : promotion.isError
      ? "promotion_failed"
      : promotion.data?.promotion_state;

  const request: ResolutionRequest = {
    root_cause: rootCause,
    mitigation,
    verification,
    trace_ids: traceIds,
    confirmed_by_human: confirmed,
  };

  return (
    <section className="resolution-panel" aria-labelledby="resolution-title">
      <div className="section-heading resolution-panel__heading">
        <div>
          <span className="eyebrow">Controlled memory lifecycle</span>
          <h2 id="resolution-title">Verify incident resolution</h2>
        </div>
        {state ? (
          <StatusBadge
            tone={
              state === "promoted"
                ? "success"
                : state === "promotion_failed"
                  ? "danger"
                  : "warning"
            }
          >
            {state}
          </StatusBadge>
        ) : null}
      </div>
      <p>
        These facts remain session-scoped until a human confirms the cited trace
        and the permanent-memory operation succeeds.
      </p>
      <div className="resolution-fields">
        <label>
          Root cause
          <textarea
            onChange={(event) => setRootCause(event.target.value)}
            rows={2}
            value={rootCause}
          />
        </label>
        <label>
          Mitigation
          <textarea
            onChange={(event) => setMitigation(event.target.value)}
            rows={2}
            value={mitigation}
          />
        </label>
        <label>
          Verification
          <textarea
            onChange={(event) => setVerification(event.target.value)}
            rows={2}
            value={verification}
          />
        </label>
      </div>
      <div className="trace-confirmation">
        <ShieldCheck size={16} aria-hidden="true" />
        <span>
          <strong>{traceIds.length} referenced trace</strong>
          <small>{traceIds.join(", ") || "Recall evidence before promotion."}</small>
        </span>
      </div>
      <label className="confirmation-check">
        <input
          checked={confirmed}
          onChange={(event) => setConfirmed(event.target.checked)}
          type="checkbox"
        />
        Human confirmation: the root cause, mitigation, verification, and
        cited trace are correct.
      </label>

      {promotion.isError ? (
        <OperationBanner
          detail="The incident remains mitigated and the resolution is stored locally. Retry the improve operation."
          state="error"
          title="Promotion failed; no learning claim was made"
        />
      ) : null}
      {promotion.data?.promotion_state === "promoted" ? (
        <div className="promotion-proof" aria-live="polite">
          <CheckCircle2 size={17} aria-hidden="true" />
          <span>
            <strong>promoted</strong>
            <small>
              Permanent memory write completed after human confirmation{" "}
              {promotion.data.confirmed_at ?? ""}
            </small>
          </span>
          <Link to={`/app/resolutions/${incidentId}`}>View proof report</Link>
        </div>
      ) : null}

      {promotion.isError ? (
        <button
          className="secondary-action"
          onClick={() => promotion.mutate(request)}
          type="button"
        >
          <RotateCcw size={15} aria-hidden="true" />
          Retry promotion
        </button>
      ) : (
        <button
          className="primary-action"
          disabled={!valid || promotion.isPending || promotion.isSuccess}
          onClick={() => promotion.mutate(request)}
          type="button"
        >
          Promote verified resolution
        </button>
      )}
    </section>
  );
}
