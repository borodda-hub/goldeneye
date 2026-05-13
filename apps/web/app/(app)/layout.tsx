import Link from "next/link";
import { Providers } from "../providers";
import { DISCLAIMER } from "../../lib/strings";
import { InstrumentSwitcher } from "@/components/instruments/InstrumentSwitcher";

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

function Wordmark() {
	return (
		<Link href="/dashboard" className="inline-flex items-baseline gap-2 group">
			<span
				className="font-serif font-light text-[22px] leading-none text-ink-1 tracking-[-0.02em] group-hover:opacity-90"
				style={{ fontVariationSettings: '"opsz" 72, "SOFT" 30' }}
			>
				Gold
				<span
					className="text-accent-bright"
					style={{
						fontStyle: "italic",
						fontVariationSettings: '"opsz" 72, "SOFT" 80',
					}}
				>
					e
				</span>
				neye
			</span>
			<span
				aria-hidden="true"
				className="font-mono text-[9px] uppercase tracking-eyebrow text-accent-deep relative -top-[2px]"
			>
				Terminal
			</span>
		</Link>
	);
}

function TopBar() {
	return (
		<header className="flex h-12 items-center justify-between border-b border-line-1 bg-surface-1 px-6 gap-4">
			<Wordmark />
			<InstrumentSwitcher className="ml-auto" />
			<button
				type="button"
				className="text-ink-3 hover:text-accent transition-colors"
				aria-label="Alerts"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="14"
					height="14"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					strokeWidth="1.5"
					strokeLinecap="round"
					strokeLinejoin="round"
				>
					<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
					<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
				</svg>
			</button>
		</header>
	);
}

function SideNav() {
	return (
		<nav className="flex w-44 shrink-0 flex-col border-r border-line-1 bg-surface-1 pt-6">
			{NAV_ITEMS.map((item, idx) => (
				<Link
					key={item.href}
					href={item.href}
					className="flex items-center gap-3 px-5 py-2.5 text-[13px] text-ink-2 hover:bg-surface-2 hover:text-ink-1 transition-colors"
				>
					<span className="font-mono text-[9px] tabular-nums text-ink-4 tracking-eyebrow">
						{String(idx + 1).padStart(2, "0")}
					</span>
					{item.label}
				</Link>
			))}
		</nav>
	);
}

function DisclaimerFooter() {
	return (
		<footer className="border-t border-line-1 bg-surface-1 px-6 py-2 text-xs text-ink-3">
			{DISCLAIMER}
		</footer>
	);
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
	return (
		<Providers>
			<div className="flex h-screen flex-col bg-surface-0 text-ink-1">
				<TopBar />
				<div className="flex flex-1 overflow-hidden">
					<SideNav />
					<main className="flex-1 overflow-auto p-6">{children}</main>
				</div>
				<DisclaimerFooter />
			</div>
		</Providers>
	);
}
