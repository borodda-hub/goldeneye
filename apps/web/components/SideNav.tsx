"use client";

import {
  CandlestickChart,
  FlaskConical,
  Gauge,
  LayoutDashboard,
  type LucideIcon,
  NotebookPen,
  Radar,
  ScrollText,
  Server,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS: { href: string; label: string; Icon: LucideIcon }[] = [
  { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { href: "/chart", label: "Chart", Icon: CandlestickChart },
  { href: "/signals", label: "Signal Lab", Icon: Radar },
  { href: "/scenarios", label: "Scenario Lab", Icon: FlaskConical },
  { href: "/journal", label: "Journal", Icon: NotebookPen },
  { href: "/ledger", label: "Ledger", Icon: ScrollText },
  { href: "/paper", label: "Paper Trading", Icon: Wallet },
  { href: "/calibration", label: "Calibration", Icon: Gauge },
  { href: "/admin", label: "Admin", Icon: Server },
];

export function SideNav() {
  const pathname = usePathname();
  return (
    <nav className="flex w-44 shrink-0 flex-col border-r border-line-1 bg-surface-1 pt-6">
      {NAV_ITEMS.map(({ href, label, Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`group flex items-center gap-3 border-l-2 px-5 py-2.5 text-[13px] transition-colors ${
              active
                ? "border-accent bg-surface-2 text-accent"
                : "border-transparent text-ink-2 hover:bg-surface-2 hover:text-ink-1"
            }`}
          >
            <Icon
              size={15}
              strokeWidth={1.5}
              aria-hidden="true"
              className={
                active
                  ? "text-accent"
                  : "text-ink-4 transition-colors group-hover:text-ink-2"
              }
            />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
