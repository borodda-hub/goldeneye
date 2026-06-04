"use client";

interface Props {
  collapsed: boolean;
  onToggle: () => void;
  label: string;
}

/**
 * Small chevron button: ▼ when expanded, ▶ when collapsed.
 * Used to drop a card down or back up.
 */
export function CollapseToggle({ collapsed, onToggle, label }: Props) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={!collapsed}
      aria-label={collapsed ? `Expand ${label}` : `Collapse ${label}`}
      className="font-mono text-xs leading-none text-ink-3 hover:text-ink-1 transition-colors px-1.5 py-0.5 -my-0.5 rounded-sm hover:bg-surface-2"
      data-testid="collapse-toggle"
    >
      {collapsed ? "▶" : "▼"}
    </button>
  );
}
