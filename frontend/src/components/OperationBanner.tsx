import clsx from "clsx";

type OperationState = "working" | "success" | "warning" | "error";

export function OperationBanner({
  title,
  detail,
  state,
}: {
  title: string;
  detail?: string;
  state: OperationState;
}) {
  return (
    <section
      className={clsx("operation-banner", `operation-banner--${state}`)}
      aria-live="polite"
    >
      <span className="operation-banner__signal" aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        {detail ? <p>{detail}</p> : null}
      </div>
    </section>
  );
}
