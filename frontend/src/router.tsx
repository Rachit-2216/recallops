import { lazy } from "react";
import { Navigate, createBrowserRouter } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { DeferredRoute } from "./app/DeferredRoute";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { DemoHome } from "./features/demo/DemoHome";

const EvidenceLibrary = lazy(() =>
  import("./features/evidence/EvidenceLibrary").then((module) => ({
    default: module.EvidenceLibrary,
  })),
);
const IncidentCockpit = lazy(() =>
  import("./features/incidents/IncidentCockpit").then((module) => ({
    default: module.IncidentCockpit,
  })),
);
const ResolutionReport = lazy(() =>
  import("./features/incidents/ResolutionReport").then((module) => ({
    default: module.ResolutionReport,
  })),
);
const MemoryExplorer = lazy(() =>
  import("./features/memory/MemoryExplorer").then((module) => ({
    default: module.MemoryExplorer,
  })),
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/app" replace />,
  },
  {
    path: "/app",
    element: (
      <ErrorBoundary>
        <AppShell />
      </ErrorBoundary>
    ),
    children: [
      {
        index: true,
        element: <DemoHome />,
      },
      {
        path: "evidence",
        element: (
          <DeferredRoute>
            <EvidenceLibrary />
          </DeferredRoute>
        ),
      },
      {
        path: "incidents/:incidentId",
        element: (
          <DeferredRoute>
            <IncidentCockpit />
          </DeferredRoute>
        ),
      },
      {
        path: "memory",
        element: (
          <DeferredRoute>
            <MemoryExplorer />
          </DeferredRoute>
        ),
      },
      {
        path: "resolutions/:incidentId",
        element: (
          <DeferredRoute>
            <ResolutionReport />
          </DeferredRoute>
        ),
      },
    ],
  },
]);
