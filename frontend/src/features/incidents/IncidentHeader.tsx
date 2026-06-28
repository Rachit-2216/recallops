import { Clock3, RadioTower, Server } from "lucide-react";

import type { IncidentDetail } from "../../api/recallops";
import { StatusBadge } from "../../components/StatusBadge";

export function IncidentHeader({
  incident,
}: {
  incident: IncidentDetail["incident"];
}) {
  return (
    <header className="incident-header">
      <div className="incident-header__identity">
        <span className="incident-id">{incident.id}</span>
        <span className="severity-chip">{incident.severity}</span>
        <StatusBadge tone="session">{incident.status}</StatusBadge>
      </div>
      <h1>{incident.title}</h1>
      <div className="incident-header__meta">
        <span>
          <Server size={14} aria-hidden="true" /> {incident.service}
        </span>
        <span>
          <Clock3 size={14} aria-hidden="true" /> Started{" "}
          {new Intl.DateTimeFormat("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "UTC",
          }).format(new Date(incident.started_at))}{" "}
          UTC
        </span>
        <span>
          <RadioTower size={14} aria-hidden="true" /> Session memory
        </span>
      </div>
    </header>
  );
}
