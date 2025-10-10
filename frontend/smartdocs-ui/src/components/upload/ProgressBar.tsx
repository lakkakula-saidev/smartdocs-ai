import React from "react";

/**
 * Accessible progress bar for upload progress visualization.
 *
 * Renders a styled gradient bar matching existing design tokens.
 * Uses ARIA role="progressbar" with current / min / max values so
 * assistive technologies can announce progress changes.
 */
export interface ProgressBarProps {
  /**
   * Fractional progress between 0 and 1.
   */
  value: number;
  /**
   * When true, visually indicates completion state.
   * (Allows parent to apply subtle finalize animations / labels.)
   */
  complete?: boolean;
  /**
   * Optional className override/extension.
   */
  className?: string;
  /**
   * Accessible label (default: "Upload progress").
   */
  "aria-label"?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  complete,
  className = "",
  "aria-label": ariaLabel = "Upload progress"
}) => {
  const pct = Math.max(0, Math.min(1, value));
  const widthPct = Math.round(pct * 100);

  return (
    <div
      className={[
        "h-2 w-full rounded bg-neutral-800 overflow-hidden",
        className
      ].join(" ")}
      role="progressbar"
      aria-label={ariaLabel}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={widthPct}
      aria-valuetext={`${widthPct}%`}
      data-complete={complete ? "true" : "false"}
    >
      <div
        className={[
          "h-full transition-all duration-300",
          "bg-gradient-to-r from-brand-400 via-brand-500 to-brand-600",
          complete ? "saturate-150" : ""
        ].join(" ")}
        style={{ width: `${widthPct}%` }}
      />
    </div>
  );
};
