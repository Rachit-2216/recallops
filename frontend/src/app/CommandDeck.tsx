import {
  Activity,
  BookOpenText,
  BrainCircuit,
  Orbit,
  RadioTower,
} from "lucide-react";
import { Link, NavLink } from "react-router-dom";

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
            <span>Offline memory</span>
            <strong>Ready</strong>
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
