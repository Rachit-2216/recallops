import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrainCircuit, Database } from "lucide-react";
import { useSearchParams, useParams } from "react-router-dom";

import {
  recallOpsApi,
  type IncidentDetail,
  type Observation,
  type RecallResult,
} from "../../api/recallops";
import { OperationBanner } from "../../components/OperationBanner";
import { StatusBadge } from "../../components/StatusBadge";
import { EmptyState } from "../../components/EmptyState";
import { MemoryInspector } from "../memory/MemoryInspector";
import { IncidentHeader } from "./IncidentHeader";
import { ObservationComposer } from "./ObservationComposer";
import { ObservationTimeline } from "./ObservationTimeline";
import { RecallComposer } from "./RecallComposer";
import { ResolutionPanel } from "./ResolutionPanel";

type ObserveInput = { content: string; observationId: string };

export function IncidentCockpit() {
  const { incidentId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const queryKey = ["incident", incidentId] as const;
  const incident = useQuery({
    queryKey,
    queryFn: ({ signal }) => recallOpsApi.getIncident(incidentId, signal),
    enabled: Boolean(incidentId),
  });
  const evidence = useQuery({
    queryKey: ["evidence"],
    queryFn: ({ signal }) => recallOpsApi.listEvidence(signal),
  });

  const observe = useMutation({
    mutationFn: ({ content, observationId }: ObserveInput) =>
      recallOpsApi.observeIncident(incidentId, content, observationId),
    onMutate: async ({ content, observationId }) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<IncidentDetail>(queryKey);
      const pending: Observation = {
        id: observationId,
        incident_id: incidentId,
        timestamp: new Date().toISOString(),
        source: "human",
        content,
        memory_status: "pending",
        memory_layer: "session",
        retry_count: 0,
      };
      queryClient.setQueryData<IncidentDetail>(queryKey, (current) =>
        current
          ? {
              ...current,
              observations: [
                ...current.observations.filter(
                  (item) => item.id !== observationId,
                ),
                pending,
              ],
            }
          : current,
      );
      return { previous };
    },
    onSuccess: (stored) => {
      queryClient.setQueryData<IncidentDetail>(queryKey, (current) =>
        current
          ? {
              ...current,
              observations: current.observations.map((item) =>
                item.id === stored.id ? stored : item,
              ),
            }
          : current,
      );
    },
  });

  const recall = useMutation<RecallResult, Error, string>({
    mutationFn: (query) => recallOpsApi.recallIncident(incidentId, query),
  });

  if (incident.isPending) {
    return (
      <section className="loading-panel" aria-live="polite">
        <span className="eyebrow">Incident session</span>
        <h1>Opening incident cockpit</h1>
        <p>Reading local timeline and memory references.</p>
      </section>
    );
  }
  if (incident.isError) {
    return (
      <section className="error-panel" role="alert">
        <span className="eyebrow">Incident unavailable</span>
        <h1>The cockpit could not be opened</h1>
        <p>{incident.error.message}</p>
      </section>
    );
  }

  const detail = incident.data;
  return (
    <div className="incident-cockpit">
      <section className="incident-stream">
        <IncidentHeader incident={detail.incident} />
        <div className="signal-strip" aria-label="Primary incident signals">
          <span>
            <strong>4.0s</strong> checkout p95
          </span>
          <span>
            <strong>+640%</strong> Redis misses
          </span>
          <span>
            <strong>deploy-418</strong> change window
          </span>
        </div>
        <ObservationComposer
          disabled={observe.isPending}
          onSubmit={(content) =>
            observe.mutate({
              content,
              observationId: crypto.randomUUID(),
            })
          }
        />
        <ObservationTimeline
          observations={detail.observations}
          onRetry={(item) =>
            observe.mutate({
              content: item.content,
              observationId: item.id,
            })
          }
        />
        {recall.data?.verification === "referenced" &&
        recall.data.trace_id ? (
          <ResolutionPanel
            incidentId={incidentId}
            traceIds={[recall.data.trace_id]}
          />
        ) : null}
      </section>

      <aside
        className="memory-inspector"
        aria-label="Memory Inspector"
        role="region"
      >
        <div className="inspector-heading">
          <BrainCircuit size={18} aria-hidden="true" />
          <div>
            <span className="eyebrow">Memory inspector</span>
            <h2>Scoped evidence</h2>
          </div>
          <StatusBadge tone="graph">graph</StatusBadge>
        </div>
        <RecallComposer
          demo={searchParams.get("demo") === "checkout"}
          disabled={recall.isPending}
          onSubmit={(query) => recall.mutate(query)}
        />
        {recall.isPending ? (
          <OperationBanner
            detail="Searching the permanent dataset and this incident session."
            state="working"
            title="Tracing memory relationships"
          />
        ) : null}
        {recall.isError ? (
          <OperationBanner
            detail={recall.error.message}
            state="error"
            title="Recall unavailable"
          />
        ) : null}
        {recall.data?.partial_memory ? (
          <OperationBanner
            detail="Some permanent evidence is still indexing. No unsupported answer will be shown."
            state="warning"
            title="Partial memory · indexing in progress"
          />
        ) : recall.data?.no_result ? (
          <EmptyState
            actionHref="/app/evidence"
            actionLabel="Inspect evidence library"
            detail="No permanent or session memory matched this question."
            title="No matching memory"
          />
        ) : recall.data ? (
          <MemoryInspector
            evidenceItems={evidence.data?.items}
            result={recall.data}
            sessionHypotheses={detail.memory_candidates}
          />
        ) : (
          <div className="inspector-empty">
            <Database size={24} aria-hidden="true" />
            <p>
              Ask a question to inspect the exact graph source, chunks, and
              lifecycle state behind an answer.
            </p>
          </div>
        )}
      </aside>
    </div>
  );
}
