import { Navigate, createBrowserRouter } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { RoutePlaceholder } from "./components/RoutePlaceholder";
import { DemoHome } from "./features/demo/DemoHome";
import { EvidenceLibrary } from "./features/evidence/EvidenceLibrary";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/app" replace />,
  },
  {
    path: "/app",
    element: <AppShell />,
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
        element: (
          <RoutePlaceholder eyebrow="Live session" title="Incident cockpit" />
        ),
      },
      {
        path: "memory",
        element: (
          <RoutePlaceholder eyebrow="Graph memory" title="Memory explorer" />
        ),
      },
      {
        path: "resolutions/:incidentId",
        element: (
          <RoutePlaceholder
            eyebrow="Verified learning"
            title="Resolution report"
          />
        ),
      },
    ],
  },
]);
