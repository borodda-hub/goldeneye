"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/chart", label: "Chart" },
  { href: "/signals", label: "Signal Lab" },
  { href: "/scenarios", label: "Scenario Lab" },
  { href: "/journal", label: "Journal" },
  { href: "/paper", label: "Paper Trading" },
  { href: "/calibration", label: "Calibration" },
  { href: "/admin", label: "Admin" },
];

export function SideNav() {
  const pathname = usePathname();
  return (
    <nav className="flex w-44 shrink-0 flex-col border-r border-line-1 bg-surface-1 pt-6">
      {NAV_ITEMS.map((item, idx) => {
        const active =
          pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 px-5 py-2.5 text-[13px] transition-colors ${
              active
                ? "bg-surface-2 text-accent"
                : "text-ink-2 hover:bg-surface-2 hover:text-ink-1"
            }`}
          >
            <span
              className={`font-mono text-[9px] tabular-nums tracking-eyebrow ${
                active ? "text-accent" : "text-ink-4"
              }`}
            >
              {String(idx + 1).padStart(2, "0")}
            </span>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
