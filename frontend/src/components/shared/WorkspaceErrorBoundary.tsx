import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

type Props = { children: ReactNode; resetKey: string };
type State = { failed: boolean };

export class WorkspaceErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Workspace render failed", error, info);
  }

  componentDidUpdate(previousProps: Props) {
    if (this.state.failed && previousProps.resetKey !== this.props.resetKey) {
      this.setState({ failed: false });
    }
  }

  render() {
    if (!this.state.failed) return this.props.children;

    return (
      <main className="mx-auto max-w-3xl px-4 py-12">
        <div className="rounded-lg border bg-background p-6 shadow-sm">
          <h1 className="text-xl font-semibold">This view could not be displayed</h1>
          <p className="mt-2 text-sm text-muted-foreground">Your session is still saved. Try loading this view again.</p>
          <Button className="mt-4" onClick={() => this.setState({ failed: false })}>Try Again</Button>
        </div>
      </main>
    );
  }
}
