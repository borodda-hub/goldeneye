"use client";

import type { DrawingTool } from "@/lib/chart/drawings";

const TOOLS: { tool: DrawingTool; label: string; title: string }[] = [
  { tool: "cursor", label: "⌖", title: "Cursor — select & move" },
  { tool: "trendline", label: "╱", title: "Trend line (2 clicks)" },
  { tool: "hline", label: "─", title: "Horizontal line (1 click)" },
  { tool: "ray", label: "↗", title: "Ray (2 clicks)" },
  { tool: "rectangle", label: "▭", title: "Rectangle (2 clicks)" },
  { tool: "fib", label: "F", title: "Fibonacci retracement (2 clicks)" },
];

interface Props {
  activeTool: DrawingTool;
  onToolChange: (tool: DrawingTool) => void;
  onClearAll: () => void;
  hasDrawings: boolean;
}

export function DrawingToolbar({
  activeTool,
  onToolChange,
  onClearAll,
  hasDrawings,
}: Props) {
  return (
    <div
      className="flex flex-col items-center gap-1 border-r border-line-1 bg-surface-0 px-1 py-2 shrink-0"
      aria-label="Drawing tools"
    >
      {TOOLS.map(({ tool, label, title }) => (
        <button
          key={tool}
          type="button"
          title={title}
          aria-label={title}
          aria-pressed={activeTool === tool}
          onClick={() => onToolChange(tool)}
          className={`flex h-7 w-7 items-center justify-center rounded font-mono text-sm transition-colors ${
            activeTool === tool
              ? "bg-accent-soft text-accent"
              : "text-ink-3 hover:text-ink-1 hover:bg-surface-2"
          }`}
        >
          {label}
        </button>
      ))}
      {hasDrawings && (
        <button
          type="button"
          title="Remove all drawings"
          aria-label="Remove all drawings"
          onClick={onClearAll}
          className="mt-1 flex h-7 w-7 items-center justify-center rounded border-t border-line-1 text-sm text-ink-4 hover:text-down hover:bg-surface-2"
        >
          🗑
        </button>
      )}
    </div>
  );
}
