import clsx from "clsx";

export type StatusTone =
  | "neutral"
  | "session"
  | "graph"
  | "warning"
  | "success"
  | "danger";

export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: StatusTone;
}) {
  return (
    <span className={clsx("status-badge", `status-badge--${tone}`)}>
      <span className="status-badge__dot" aria-hidden="true" />
      {children}
    </span>
  );
}
