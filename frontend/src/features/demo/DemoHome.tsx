import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpenText,
  Database,
  Gauge,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../../api/client";
import { recallOpsApi } from "../../api/recallops";
import { OperationBanner } from "../../components/OperationBanner";
import { StatusBadge } from "../../components/StatusBadge";

type DemoHomeProps = {
  publicDemo?: boolean;
};

export function DemoHome({
  publicDemo = import.meta.env.VITE_PUBLIC_DEMO === "true",
}: DemoHomeProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [adminToken, setAdminToken] = useState("");
  const evidence = useQuery({
    queryKey: ["evidence"],
    queryFn: ({ signal }) => recallOpsApi.listEvidence(signal),
  });
  const readyEvidence =
    evidence.data?.items.filter((item) => item.status === "ready").length ?? 0;
  const seedRequired = evidence.isSuccess && readyEvidence === 0;

  const reset = useMutation({
    mutationFn: recallOpsApi.resetDemo,
    onSuccess: (result) => {
      navigate(`/app/incidents/${result.incident_id}?demo=checkout`);
    },
  });
  const seed = useMutation({
    mutationFn: () => recallOpsApi.seedDemo(adminToken),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["evidence"] });
    },
  });

  const resetError =
    reset.error instanceof ApiError
      ? reset.error.message
      : reset.error
        ? "The incident could not be reset."
        : null;

  return (
    <section className="demo-home" aria-labelledby="demo-title">
      <header className="page-header">
        <div>
          <span className="eyebrow">Incident queue / deterministic fixture</span>
          <h1 id="demo-title">Memory-assisted incident response</h1>
          <p>
            Reconstruct a checkout outage from stored evidence, then verify
            what the system may promote to permanent memory.
          </p>
        </div>
        <StatusBadge tone="session">Synthetic data only</StatusBadge>
      </header>

      <div className="demo-grid">
        <article className="demo-card demo-card--primary">
          <div className="demo-card__index">DEMO / 01</div>
          <div className="demo-card__title-row">
            <div>
              <span className="eyebrow">SEV1 · checkout-api</span>
              <h2>Checkout latency after deploy-418</h2>
            </div>
            <span className="severity-chip">SEV1</span>
          </div>
          <p className="demo-card__summary">
            Correlate a 4-second p95 spike and a 640% Redis miss increase with a
            prior, verified session-TTL incident.
          </p>

          <dl className="signal-grid">
            <div>
              <dt>Deploy</dt>
              <dd>deploy-418</dd>
            </div>
            <div>
              <dt>Evidence</dt>
              <dd>{readyEvidence || "—"} ready</dd>
            </div>
            <div>
              <dt>Mode</dt>
              <dd>offline-safe</dd>
            </div>
          </dl>

          {reset.isPending ? (
            <OperationBanner
              title="Restoring incident timeline"
              detail="Replacing local session state; permanent evidence is untouched."
              state="working"
            />
          ) : null}
          {resetError ? (
            <p className="inline-error" role="alert">
              {resetError}
            </p>
          ) : null}

          <button
            className="primary-action"
            disabled={reset.isPending || seedRequired}
            onClick={() => reset.mutate()}
            type="button"
          >
            <RotateCcw size={17} aria-hidden="true" />
            Load Checkout Outage Demo
            <ArrowRight size={17} aria-hidden="true" />
          </button>
        </article>

        <aside className="readiness-panel" aria-labelledby="readiness-title">
          <div className="readiness-panel__heading">
            <Database size={18} aria-hidden="true" />
            <h2 id="readiness-title">Dataset readiness</h2>
          </div>
          <div className="readiness-line">
            <span>recallops_evidence_v1</span>
            <StatusBadge
              tone={
                evidence.isError
                  ? "danger"
                  : readyEvidence > 0
                    ? "success"
                    : "warning"
              }
            >
              {evidence.isPending
                ? "checking"
                : readyEvidence > 0
                  ? `${readyEvidence} ready`
                  : "seed required"}
            </StatusBadge>
          </div>

          {seedRequired && publicDemo ? (
            <div className="setup-guidance">
              <ShieldCheck size={18} aria-hidden="true" />
              <div>
                <strong>Setup guidance</strong>
                <p>
                  The public dataset is not ready. Contact the demo operator;
                  credentials are never accepted in this screen.
                </p>
              </div>
            </div>
          ) : null}

          {seedRequired && !publicDemo ? (
            <form
              className="seed-form"
              onSubmit={(event) => {
                event.preventDefault();
                seed.mutate();
              }}
            >
              <label htmlFor="demo-admin-token">Demo admin token</label>
              <input
                id="demo-admin-token"
                onChange={(event) => setAdminToken(event.target.value)}
                type="password"
                value={adminToken}
              />
              <button
                className="secondary-action"
                disabled={!adminToken || seed.isPending}
                type="submit"
              >
                Seed synthetic evidence
              </button>
            </form>
          ) : null}

          <div className="budget-readout">
            <Gauge size={18} aria-hidden="true" />
            <div>
              <span>Estimated internal cost</span>
              <strong>0 live credits</strong>
              <small>Protected reserve remains untouched in offline mode.</small>
            </div>
          </div>
          <Link className="text-link" to="/app/evidence">
            <BookOpenText size={16} aria-hidden="true" />
            Inspect permanent evidence
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        </aside>
      </div>
    </section>
  );
}
