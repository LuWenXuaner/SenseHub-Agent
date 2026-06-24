import { Component, ReactNode } from "react";

type Props = { children: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-6 text-center">
          <h1 className="text-lg font-semibold text-text-primary">页面出现异常</h1>
          <p className="max-w-md text-sm text-text-secondary">{this.state.error.message}</p>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              this.setState({ error: null });
              window.location.href = "/";
            }}
          >
            重新加载
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
