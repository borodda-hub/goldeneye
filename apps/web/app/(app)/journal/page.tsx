import { EMPTY_STATE } from "../../../lib/strings";

export default function JournalPage() {
	return (
		<div className="flex flex-col gap-4">
			<h1 className="text-xl font-semibold text-ink-1">Decision Journal</h1>
			<p className="text-sm text-ink-3">{EMPTY_STATE.journal}</p>
		</div>
	);
}
