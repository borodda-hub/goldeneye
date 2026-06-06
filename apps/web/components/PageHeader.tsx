import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface Props {
  icon: LucideIcon;
  title: string;
  /** Mono uppercase strapline under the title. */
  subtitle?: string;
  /** Optional right-aligned slot (status chip, actions). */
  right?: ReactNode;
  className?: string;
}

/**
 * Consistent in-app page header: a gold-accented icon chip beside the title and
 * an optional mono strapline. Shared across the dashboard/lab/admin pages so
 * every screen opens the same way.
 */
export function PageHeader({
  icon: Icon,
  title,
  subtitle,
  right,
  className = "",
}: Props) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <span className="flex h-8 w-8 items-center justify-center rounded-sm border border-line-1 bg-surface-1 text-accent">
        <Icon size={16} strokeWidth={1.5} aria-hidden="true" />
      </span>
      <div className="flex min-w-0 flex-col">
        <h1 className="text-lg font-semibold leading-tight text-ink-1">
          {title}
        </h1>
        {subtitle && (
          <span className="font-mono text-[10px] uppercase tracking-widest text-ink-4">
            {subtitle}
          </span>
        )}
      </div>
      {right && <div className="ml-auto flex items-center gap-3">{right}</div>}
    </div>
  );
}
