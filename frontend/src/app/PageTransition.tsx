import { m } from "motion/react";

export function PageTransition({
  children,
  routeKey,
}: {
  children: React.ReactNode;
  routeKey: string;
}) {
  return (
    <m.section
      animate={{ opacity: 1, y: 0 }}
      aria-label="Current workspace"
      className="page-transition"
      data-route={routeKey}
      initial={{ opacity: 1, y: 12 }}
      key={routeKey}
      role="region"
      transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </m.section>
  );
}
