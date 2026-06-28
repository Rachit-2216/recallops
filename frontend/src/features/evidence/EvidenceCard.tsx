import {
  ArchiveX,
  CalendarDays,
  Database,
  FileText,
  Fingerprint,
} from "lucide-react";

import type { EvidenceItem } from "../../api/recallops";
import { StatusBadge, type StatusTone } from "../../components/StatusBadge";

const statusTone: Record<EvidenceItem["status"], StatusTone> = {
  queued: "warning",
  processing: "session",
  ready: "success",
  failed: "danger",
  forgotten: "neutral",
};

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Date not supplied";
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

export function EvidenceCard({ item }: { item: EvidenceItem }) {
  const forgotten = item.status === "forgotten";
  return (
    <article
      className={`evidence-card${forgotten ? " evidence-card--forgotten" : ""}`}
      data-testid={`evidence-${item.status}`}
    >
      <div className="evidence-card__topline">
        <StatusBadge tone={statusTone[item.status]}>{item.status}</StatusBadge>
        {item.is_stale ? <span className="stale-marker">Stale</span> : null}
      </div>
      <div className="evidence-card__identity">
        <FileText size={20} aria-hidden="true" />
        <div>
          <h2>{item.name}</h2>
          <span>{item.kind}</span>
        </div>
      </div>
      <dl className="evidence-metadata">
        <div>
          <dt>
            <Fingerprint size={14} aria-hidden="true" /> Data ID
          </dt>
          <dd title={item.data_id}>{item.data_id.slice(0, 8)}</dd>
        </div>
        <div>
          <dt>
            <CalendarDays size={14} aria-hidden="true" /> Source date
          </dt>
          <dd>{formatDate(item.source_date)}</dd>
        </div>
        <div>
          <dt>
            <Database size={14} aria-hidden="true" /> Memory layer
          </dt>
          <dd>{item.memory_layer}</dd>
        </div>
      </dl>
      {forgotten ? (
        <p className="forgotten-note">
          <ArchiveX size={15} aria-hidden="true" />
          Excluded from active evidence; retained in local audit history.
        </p>
      ) : null}
    </article>
  );
}
