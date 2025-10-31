import React, { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, errorInfo: ErrorInfo, reset: () => void) => ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary component to catch React errors and prevent full app crashes
 *
 * Usage:
 * <ErrorBoundary>
 *   <App />
 * </ErrorBoundary>
 *
 * Or with custom fallback:
 * <ErrorBoundary fallback={(error, errorInfo, reset) => <CustomErrorUI />}>
 *   <App />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error details to console
    console.error('[ErrorBoundary] Caught error:', error);
    console.error('[ErrorBoundary] Component stack:', errorInfo.componentStack);

    // Update state with error info for display
    this.setState({
      error,
      errorInfo,
    });

    // TODO: Send error to logging service (e.g., Sentry, LogRocket)
    // Example: logErrorToService(error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      // Custom fallback UI from props
      if (this.props.fallback) {
        return this.props.fallback(
          this.state.error,
          this.state.errorInfo!,
          this.handleReset
        );
      }

      // Default fallback UI
      return (
        <div className="error-boundary-fallback">
          <div className="error-boundary-content">
            <div className="error-icon">⚠️</div>
            <h1>Something Went Wrong</h1>
            <p className="error-message">
              CardFlux encountered an unexpected error. Your data is safe.
            </p>

            <div className="error-details">
              <details>
                <summary>Technical Details (for debugging)</summary>
                <div className="error-stack">
                  <p><strong>Error:</strong> {this.state.error.toString()}</p>
                  {this.state.error.stack && (
                    <pre>{this.state.error.stack}</pre>
                  )}
                  {this.state.errorInfo && (
                    <>
                      <p><strong>Component Stack:</strong></p>
                      <pre>{this.state.errorInfo.componentStack}</pre>
                    </>
                  )}
                </div>
              </details>
            </div>

            <div className="error-actions">
              <button
                className="btn btn-primary"
                onClick={this.handleReset}
              >
                Try Again
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => window.location.reload()}
              >
                Reload App
              </button>
            </div>

            <p className="error-help">
              If this problem persists, please restart the application or contact support.
            </p>
          </div>

          <style>{`
            .error-boundary-fallback {
              display: flex;
              align-items: center;
              justify-content: center;
              min-height: 100vh;
              background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
              color: #e0e0e0;
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              padding: 20px;
            }

            .error-boundary-content {
              max-width: 600px;
              text-align: center;
              background: #1e1e1e;
              border: 1px solid #333;
              border-radius: 12px;
              padding: 40px;
              box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            }

            .error-icon {
              font-size: 64px;
              margin-bottom: 20px;
              animation: pulse 2s ease-in-out infinite;
            }

            @keyframes pulse {
              0%, 100% { transform: scale(1); opacity: 1; }
              50% { transform: scale(1.1); opacity: 0.8; }
            }

            .error-boundary-content h1 {
              font-size: 28px;
              margin: 0 0 16px 0;
              color: #fff;
            }

            .error-message {
              font-size: 16px;
              color: #b0b0b0;
              margin-bottom: 24px;
            }

            .error-details {
              margin: 24px 0;
              text-align: left;
            }

            .error-details summary {
              cursor: pointer;
              color: #888;
              font-size: 14px;
              padding: 8px 12px;
              background: #252525;
              border-radius: 6px;
              user-select: none;
            }

            .error-details summary:hover {
              background: #2a2a2a;
              color: #aaa;
            }

            .error-stack {
              padding: 16px;
              margin-top: 12px;
              background: #0a0a0a;
              border: 1px solid #333;
              border-radius: 6px;
              max-height: 300px;
              overflow-y: auto;
            }

            .error-stack pre {
              font-size: 12px;
              line-height: 1.5;
              color: #ccc;
              white-space: pre-wrap;
              word-break: break-word;
              margin: 8px 0;
              font-family: 'Courier New', monospace;
            }

            .error-stack strong {
              color: #fff;
              display: block;
              margin-top: 12px;
            }

            .error-actions {
              display: flex;
              gap: 12px;
              justify-content: center;
              margin: 24px 0;
            }

            .error-help {
              font-size: 14px;
              color: #777;
              margin-top: 24px;
            }

            .btn {
              padding: 12px 24px;
              border: none;
              border-radius: 6px;
              font-size: 14px;
              font-weight: 600;
              cursor: pointer;
              transition: all 0.2s;
            }

            .btn-primary {
              background: #4CAF50;
              color: white;
            }

            .btn-primary:hover {
              background: #45a049;
              transform: translateY(-1px);
              box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
            }

            .btn-secondary {
              background: #333;
              color: #e0e0e0;
            }

            .btn-secondary:hover {
              background: #444;
              transform: translateY(-1px);
            }

            .btn:active {
              transform: translateY(0);
            }
          `}</style>
        </div>
      );
    }

    // No error, render children normally
    return this.props.children;
  }
}
