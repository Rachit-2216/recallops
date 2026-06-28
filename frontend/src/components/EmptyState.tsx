import { SearchX } from "lucide-react";
import { Link } from "react-router-dom";

export function EmptyState({
  title,
  detail,
  actionHref,
  actionLabel,
}: {
  title: string;
  detail: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <section className="empty-state" aria-live="polite">
      <SearchX size={22} aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
        {actionHref && actionLabel ? (
          <Link to={actionHref}>{actionLabel}</Link>
        ) : null}
      </div>
    </section>
  );
}
