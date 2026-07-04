export type ConstellationNode = {
  id: string;
  label: string;
  kind: "change" | "dependency" | "failure" | "symptom" | "memory" | "proof";
  detail: string;
  color: string;
  position: readonly [number, number, number];
};

export const CONSTELLATION_NODES: ConstellationNode[] = [
  {
    id: "change",
    label: "Global WAF change",
    kind: "change",
    detail: "The configuration change that entered global propagation.",
    color: "#ffb657",
    position: [-2.55, 1.25, 0.2],
  },
  {
    id: "execute",
    label: "FL1 execute object",
    kind: "dependency",
    detail: "A shared dependency removed by the propagated configuration.",
    color: "#a99cff",
    position: [-1.05, -1.65, 0.85],
  },
  {
    id: "nil",
    label: "Nil dereference",
    kind: "failure",
    detail: "The failure mechanism connected to the affected request path.",
    color: "#ff756d",
    position: [1.4, -1.65, -0.25],
  },
  {
    id: "errors",
    label: "HTTP 500 errors",
    kind: "symptom",
    detail: "The customer-visible symptom affecting 28% of HTTP traffic.",
    color: "#ff756d",
    position: [2.7, 0.35, 0.3],
  },
  {
    id: "prior",
    label: "November 18 outage",
    kind: "memory",
    detail: "A prior incident recalled for its shared global propagation risk.",
    color: "#68f7e2",
    position: [1.05, 1.95, -0.55],
  },
  {
    id: "proof",
    label: "Verified mitigation",
    kind: "proof",
    detail: "Human-confirmed mitigation promoted only after trace verification.",
    color: "#73e6a5",
    position: [-1.2, 2.05, 0.55],
  },
];

export const CONSTELLATION_EDGES = [
  ["change", "execute"],
  ["execute", "nil"],
  ["nil", "errors"],
  ["errors", "prior"],
  ["prior", "proof"],
] as const;
