import { AlertTriangle, Check, RefreshCw } from "lucide-react";

import type { Observation } from "../../api/recallops";

type ObservationTimelineProps = {
  observations: Observation[];
  onRetry: (observation: Observation) => void;
};

export function ObservationTimeline({
  observations,
  onRetry,
}: ObservationTimelineProps) {
  return (
    <section className="timeline" aria-labelledby="timeline-title">
      <div className="section-heading">
        <span className="eyebrow">Session timeline</span>
        <h2 id="timeline-title">{observations.length} observations</h2>
      </div>
      <ol>
        {observations.map((observation) => {
          const pending = observation.memory_status === "pending";
          return (
            <li className="timeline-entry" key={observation.id}>
              <div className="timeline-entry__rail">
                <span />
              </div>
              <div className="timeline-entry__body">
                <div className="timeline-entry__meta">
                  <time dateTime={observation.timestamp}>
                    {new Intl.DateTimeFormat("en-GB", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                      timeZone: "UTC",
                    }).format(new Date(observation.timestamp))}
                  </time>
                  <span>{observation.source}</span>
                  <span
                    className={
                      pending ? "memory-state pending" : "memory-state stored"
                    }
                  >
                    {pending ? (
                      <AlertTriangle size={12} aria-hidden="true" />
                    ) : (
                      <Check size={12} aria-hidden="true" />
                    )}
                    {pending ? "pending · not permanent" : "session stored"}
                  </span>
                </div>
                <p>{observation.content}</p>
                {pending ? (
                  <button
                    className="retry-action"
                    onClick={() => onRetry(observation)}
                    type="button"
                  >
                    <RefreshCw size={13} aria-hidden="true" />
                    Retry session write
                  </button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
