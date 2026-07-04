import { Suspense } from "react";

export function DeferredRoute({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <section className="loading-panel" aria-live="polite">
          <span className="eyebrow">Opening workspace</span>
          <h1>Synchronizing route</h1>
          <p>Loading only the interface required for this view.</p>
        </section>
      }
    >
      {children}
    </Suspense>
  );
}
