import { Component, type ReactNode } from "react";

type ErrorBoundaryState = {
  failed: boolean;
};

export class ErrorBoundary extends Component<
  { children: ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true };
  }

  componentDidCatch() {
    // Rendering failures are intentionally not echoed into the UI.
  }

  render() {
    if (this.state.failed) {
      return (
        <section className="error-panel" role="alert">
          <span className="eyebrow">Interface recovery</span>
          <h1>This view could not be rendered</h1>
          <p>Your incident data was not changed.</p>
          <button
            className="secondary-action"
            onClick={() => this.setState({ failed: false })}
            type="button"
          >
            Retry view
          </button>
        </section>
      );
    }
    return this.props.children;
  }
}
