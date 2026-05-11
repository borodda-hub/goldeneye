import { EMPTY_STATE } from "../../../lib/strings";

export default function ChartPage() {
	return (
		<div className="flex flex-col gap-4">
			<h1 className="text-xl font-semibold text-ink-1">Chart</h1>
			<p className="text-sm text-ink-3">{EMPTY_STATE.chart}</p>
		</div>
	);
}
