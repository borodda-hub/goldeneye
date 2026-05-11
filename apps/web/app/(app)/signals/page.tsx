import { EMPTY_STATE } from "../../../lib/strings";

export default function SignalsPage() {
	return (
		<div className="flex flex-col gap-4">
			<h1 className="text-xl font-semibold text-ink-1">Signal Lab</h1>
			<p className="text-sm text-ink-3">{EMPTY_STATE.signals}</p>
		</div>
	);
}
