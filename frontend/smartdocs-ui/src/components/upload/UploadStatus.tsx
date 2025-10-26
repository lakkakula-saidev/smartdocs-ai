import React from "react";

/**
 * UploadStatus
 *
 * Presents current upload outcome messages (error / success) with proper accessibility semantics.
 * - Error messages use role="alert" (assertive polite interruption).
 * - Success messages use role="status" (polite, non-interruptive).
 *
 * Purely presentational; parent owns state.
 */
export interface UploadStatusProps {
  /**
   * Error message (if any). Takes precedence over success display.
   */
  error?: string;
  /**
   * Successful document ID (if upload succeeded).
   */
  successId?: string | null;
  /**
   * Optional flag to suppress rendering entirely when no messages.
   */
  hideWhenEmpty?: boolean;
  /**
   * Custom className override/extension.
   */
  className?: string;
  /**
   * Optional callback to clear error (renders a dismiss button if provided).
   */
  onDismissError?: () => void;
}

/**
 * UploadStatus component.
 */
export const UploadStatus: React.FC<UploadStatusProps> = ({
  error,
  successId,
  hideWhenEmpty = true,
  className = "",
  onDismissError
}) => {
  if (hideWhenEmpty && !error && !successId) return null;

  if (error) {
    return (
      <div
        role="alert"
        aria-live="assertive"
        className={[
          "mt-1 text-[0.65rem] font-medium flex items-start gap-2",
          "text-red-400",
          className
        ].join(" ")}
      >
        <span className="flex-1 break-words">{error}</span>
        {onDismissError && (
          <button
            type="button"
            onClick={onDismissError}
            className="text-[0.55rem] uppercase tracking-wide text-red-300/70 hover:text-red-200 transition"
            aria-label="Dismiss upload error"
          >
            Dismiss
          </button>
        )}
      </div>
    );
  }

  if (successId) {
    return (
      <p
        role="status"
        aria-live="polite"
        className={[
          "mt-1 text-[0.65rem] font-medium",
          "text-emerald-400",
          className
        ].join(" ")}
      >
        Upload successful. ID: <code className="text-emerald-300">{successId}</code>
      </p>
    );
  }

  return null;
};
