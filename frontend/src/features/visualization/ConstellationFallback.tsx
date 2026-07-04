import type { ConstellationNode } from "./constellationData";

export function ConstellationFallback({
  nodes,
  selectedId,
}: {
  nodes: ConstellationNode[];
  selectedId: string;
}) {
  return (
    <svg
      aria-label="Static incident memory constellation"
      className="constellation-fallback"
      role="img"
      viewBox="0 0 720 620"
    >
      <defs>
        <radialGradient id="core-glow">
          <stop offset="0" stopColor="#68f7e2" stopOpacity=".34" />
          <stop offset=".45" stopColor="#68f7e2" stopOpacity=".08" />
          <stop offset="1" stopColor="#68f7e2" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="orbit-stroke" x1="0" x2="1">
          <stop stopColor="#68f7e2" stopOpacity=".15" />
          <stop offset=".5" stopColor="#ffb657" stopOpacity=".5" />
          <stop offset="1" stopColor="#a99cff" stopOpacity=".12" />
        </linearGradient>
      </defs>
      <circle cx="360" cy="305" fill="url(#core-glow)" r="230" />
      <ellipse
        cx="360"
        cy="305"
        fill="none"
        rx="285"
        ry="166"
        stroke="url(#orbit-stroke)"
      />
      <ellipse
        cx="360"
        cy="305"
        fill="none"
        rx="196"
        ry="268"
        stroke="url(#orbit-stroke)"
        transform="rotate(58 360 305)"
      />
      <path
        d="M155 230 270 438 470 438 575 335 444 150 265 145Z"
        fill="none"
        stroke="rgba(104,247,226,.28)"
      />
      <circle
        cx="360"
        cy="305"
        fill="#0a1616"
        r="62"
        stroke="#68f7e2"
        strokeWidth="2"
      />
      <path
        d="m360 254 44 25v51l-44 25-44-25v-51Z"
        fill="rgba(104,247,226,.08)"
        stroke="#68f7e2"
      />
      {nodes.map((node, index) => {
        const points = [
          [155, 230],
          [270, 438],
          [470, 438],
          [575, 335],
          [444, 150],
          [265, 145],
        ];
        const [cx, cy] = points[index];
        const active = node.id === selectedId;
        return (
          <g key={node.id}>
            <circle
              cx={cx}
              cy={cy}
              fill={active ? node.color : "#0b1112"}
              fillOpacity={active ? 0.28 : 1}
              r={active ? 18 : 12}
              stroke={node.color}
              strokeWidth={active ? 3 : 1.5}
            />
            <circle
              cx={cx}
              cy={cy}
              fill={node.color}
              r="3"
            />
          </g>
        );
      })}
    </svg>
  );
}
