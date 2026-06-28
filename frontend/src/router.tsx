import { Navigate, createBrowserRouter } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { DemoHome } from "./features/demo/DemoHome";
import { EvidenceLibrary } from "./features/evidence/EvidenceLibrary";
import { IncidentCockpit } from "./features/incidents/IncidentCockpit";
import { ResolutionReport } from "./features/incidents/ResolutionReport";
import { MemoryExplorer } from "./features/memory/MemoryExplorer";

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
        element: <EvidenceLibrary />,
      },
      {
        path: "incidents/:incidentId",
        element: <IncidentCockpit />,
      },
      {
        path: "memory",
        element: <MemoryExplorer />,
      },
      {
        path: "resolutions/:incidentId",
        element: <ResolutionReport />,
      },
    ],
  },
]);
