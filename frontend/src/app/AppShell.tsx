import { Outlet, useLocation } from "react-router-dom";

import { CommandDeck } from "./CommandDeck";
import { PageTransition } from "./PageTransition";

export function AppShell() {
  const location = useLocation();

  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">
        Skip to incident workspace
      </a>
      <div className="orbital-atmosphere" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <CommandDeck />
      <main id="main-content" className="app-workspace">
        <PageTransition routeKey={location.pathname}>
          <Outlet />
        </PageTransition>
      </main>
    </div>
  );
}
