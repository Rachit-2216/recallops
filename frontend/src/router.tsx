import { Navigate, createBrowserRouter } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { RoutePlaceholder } from "./components/RoutePlaceholder";

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
        element: <RoutePlaceholder eyebrow="Demo 01" title="Incident queue" />,
      },
      {
        path: "evidence",
        element: (
          <RoutePlaceholder
            eyebrow="Permanent memory"
            title="Evidence library"
          />
        ),
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
