export function RoutePlaceholder({
  eyebrow,
  title,
}: {
  eyebrow: string;
  title: string;
}) {
  return (
    <section className="placeholder-panel">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p>The operational module is initializing.</p>
    </section>
  );
}
