import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  BookOpenText,
  BrainCircuit,
  Orbit,
  RadioTower,
} from "lucide-react";
import { Link, NavLink } from "react-router-dom";

import { recallOpsApi } from "../api/recallops";
import { StatusBadge } from "../components/StatusBadge";

const navigation = [
  { label: "Incidents", to: "/app", icon: Activity, end: true },
  {
    label: "Evidence",
    to: "/app/evidence",
    icon: BookOpenText,
    end: false,
  },
  {
    label: "Memory",
    to: "/app/memory",
    icon: BrainCircuit,
    end: false,
  },
];

export function CommandDeck() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => recallOpsApi.getHealth(signal),
    refetchInterval: 30_000,
  });
  const memory = health.data?.memory;
  const memoryReady = memory?.reachable === true && memory.dataset_ready;
  const memoryLabel =
    memory?.mode === "live"
      ? "Cognee memory"
      : memory?.mode === "fake"
        ? "Offline memory"
        : "Memory status";
  const memoryStatus = health.isPending
    ? "Checking"
    : memoryReady
      ? memory?.mode === "live"
        ? "Connected"
        : "Ready"
      : "Degraded";

  return (
    <>
      <header
        aria-label="RecallOps command deck"
        className="command-deck"
      >
        <Link aria-label="RecallOps home" className="brand-lockup" to="/app">
          <span className="brand-orbit" aria-hidden="true">
            <Orbit size={22} strokeWidth={1.4} />
            <i />
          </span>
          <span className="brand-wordmark">
            <strong>RECALL</strong>
            <small>OPS</small>
          </span>
        </Link>

        <div className="command-status" aria-label="System status">
          <StatusBadge tone="session">Public case study</StatusBadge>
          <span className="memory-mode">
            <RadioTower size={14} aria-hidden="true" />
            <span>{memoryLabel}</span>
            <strong>{memoryStatus}</strong>
          </span>
        </div>
      </header>

      <nav aria-label="Primary navigation" className="command-nav">
        {navigation.map(({ label, to, icon: Icon, end }) => (
          <NavLink
            className={({ isActive }) =>
              `command-link${isActive ? " command-link--active" : ""}`
            }
            end={end}
            key={to}
            to={to}
          >
            <Icon size={16} strokeWidth={1.7} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  );
}
