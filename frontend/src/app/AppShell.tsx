import {
  Activity,
  BookOpenText,
  BrainCircuit,
  CircleGauge,
  RadioTower,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

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
    label: "Memory graph",
    to: "/app/memory",
    icon: BrainCircuit,
    end: false,
  },
];

export function AppShell() {
  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">
        Skip to incident workspace
      </a>
      <aside className="nav-rail" aria-label="Primary navigation">
        <div className="brand-lockup" aria-label="RecallOps">
          <span className="brand-lockup__signal" aria-hidden="true">
            R//
          </span>
          <span>
            <strong>RECALL</strong>
            <small>OPS</small>
          </span>
        </div>

        <div className="system-label">Incident memory console</div>
        <nav>
          {navigation.map(({ label, to, icon: Icon, end }) => (
            <NavLink
              className={({ isActive }) =>
                `nav-link${isActive ? " nav-link--active" : ""}`
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

        <div className="nav-rail__telemetry">
          <StatusBadge tone="session">Public case study</StatusBadge>
          <div className="telemetry-row">
            <span>
              <RadioTower size={14} aria-hidden="true" /> Memory
            </span>
            <strong>FAKE / READY</strong>
          </div>
          <div className="reserve-meter">
            <div className="reserve-meter__label">
              <span>
                <CircleGauge size={14} aria-hidden="true" /> Protected reserve
              </span>
              <strong>6.0M</strong>
            </div>
            <div
              className="reserve-meter__track"
              role="meter"
              aria-label="Protected Cognee credit reserve"
              aria-valuemin={0}
              aria-valuemax={14}
              aria-valuenow={6}
            >
              <span />
            </div>
          </div>
        </div>
      </aside>

      <main id="main-content" className="app-workspace">
        <Outlet />
      </main>
    </div>
  );
}
