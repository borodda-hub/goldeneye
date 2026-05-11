import Link from "next/link";
import { Providers } from "../providers";
import { DISCLAIMER } from "../../lib/strings";

const NAV_ITEMS = [
	{ href: "/dashboard", label: "Dashboard", icon: "⬛" },
	{ href: "/chart", label: "Chart", icon: "📈" },
	{ href: "/signals", label: "Signal Lab", icon: "⚡" },
	{ href: "/scenarios", label: "Scenario Lab", icon: "🔬" },
	{ href: "/journal", label: "Journal", icon: "📓" },
	{ href: "/paper", label: "Paper Trading", icon: "📋" },
	{ href: "/admin", label: "Admin", icon: "⚙" },
];

function TopBar() {
	return (
		<header className="flex h-12 items-center justify-between border-b border-line-1 bg-surface-1 px-6">
			<span className="text-sm font-semibold tracking-widest text-ink-1">
				NGTI
			</span>
			<span className="rounded bg-surface-2 px-3 py-1 font-mono text-xs text-ink-2">
				NG · Henry Hub
			</span>
			<button
				type="button"
				className="text-ink-3 hover:text-ink-1"
				aria-label="Alerts"
			>
				🔔
			</button>
		</header>
	);
}

function SideNav() {
	return (
		<nav className="flex w-48 shrink-0 flex-col border-r border-line-1 bg-surface-1 pt-4">
			{NAV_ITEMS.map((item) => (
				<Link
					key={item.href}
					href={item.href}
					className="flex items-center gap-3 px-4 py-2 text-sm text-ink-2 hover:bg-surface-2 hover:text-ink-1"
				>
					<span className="text-xs">{item.icon}</span>
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
