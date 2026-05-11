"use client";

interface Props {
  disabled: boolean;
  running: boolean;
  onRun: () => void;
}

export function RunButton({ disabled, running, onRun }: Props) {
  const baseClass =
    "font-mono text-xs uppercase tracking-widest px-4 py-2 border transition-colors";
  const stateClass =
    disabled || running
      ? "border-line-1 text-ink-4 cursor-not-allowed"
      : "border-accent text-accent hover:bg-surface-2";

  return (
    <button
      type="button"
      onClick={onRun}
      disabled={disabled || running}
      aria-busy={running}
      className={`${baseClass} ${stateClass}`}
    >
      {running ? "Running…" : "Run Scenario"}
    </button>
  );
}
