"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { JournalEntry } from "../../app/(app)/journal/types";
import type { Trade } from "../../app/(app)/paper/types";
import { openPaperTrade } from "../../lib/api";
import { queryKeys } from "../../lib/queries";

interface Props {
  journalEntries: JournalEntry[];
}

interface FormState {
  contract_code: string;
  side: "long" | "short";
  size_contracts: number;
  entry_price: number;
  stop_loss: string;
  take_profit: string;
  rationale: string;
  journal_ref: string;
}

const initial: FormState = {
  contract_code: "",
  side: "long",
  size_contracts: 1,
  entry_price: 0,
  stop_loss: "",
  take_profit: "",
  rationale: "",
  journal_ref: "",
};

export function NewTradeForm({ journalEntries }: Props) {
  const [form, setForm] = useState<FormState>(initial);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const mutation = useMutation<Trade, Error, void>({
    mutationFn: async () => {
      const body = {
        instrument: "NG",
        contract_code: form.contract_code.trim() || undefined,
        side: form.side,
        size_contracts: form.size_contracts,
        entry_price: form.entry_price,
        stop_loss: form.stop_loss ? Number(form.stop_loss) : undefined,
        take_profit: form.take_profit ? Number(form.take_profit) : undefined,
        rationale: form.rationale.trim() || undefined,
        journal_ref: form.journal_ref || undefined,
      };
      return (await openPaperTrade(body)) as Trade;
    },
    onMutate: () => {
      setErrorMsg(null);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.paperTrades("open"),
      });
      queryClient.invalidateQueries({ queryKey: ["paper", "equity-curve"] });
      setForm(initial);
    },
    onError: (err) => {
      const msg = err?.message ?? "unknown error";
      if (msg.includes("409")) {
        setErrorMsg("Leverage cap exceeded (10× equity).");
      } else {
        setErrorMsg(msg);
      }
    },
  });

  const valid = form.size_contracts > 0 && form.entry_price > 0;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (valid && !mutation.isPending) mutation.mutate();
      }}
      className="border border-line-1 bg-surface-1 p-3 flex flex-col gap-3"
    >
      <h2 className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
        New Trade
      </h2>

      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Contract Code
        </span>
        <input
          className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2"
          placeholder="e.g. NGF26"
          value={form.contract_code}
          onChange={(e) =>
            setForm((f) => ({ ...f, contract_code: e.target.value }))
          }
        />
      </label>

      <div className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Side
        </span>
        <div className="flex gap-0 border border-line-1">
          <button
            type="button"
            onClick={() => setForm((f) => ({ ...f, side: "long" }))}
            className={`flex-1 font-mono text-xs uppercase tracking-widest py-1.5 ${
              form.side === "long"
                ? "bg-up-soft text-up"
                : "text-ink-3 hover:bg-surface-2"
            }`}
            aria-pressed={form.side === "long"}
          >
            Long
          </button>
          <button
            type="button"
            onClick={() => setForm((f) => ({ ...f, side: "short" }))}
            className={`flex-1 font-mono text-xs uppercase tracking-widest py-1.5 ${
              form.side === "short"
                ? "bg-down-soft text-down"
                : "text-ink-3 hover:bg-surface-2"
            }`}
            aria-pressed={form.side === "short"}
          >
            Short
          </button>
        </div>
      </div>

      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Size (contracts)
        </span>
        <input
          type="number"
          step="0.1"
          min={0.1}
          className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2 tabular-nums"
          value={form.size_contracts}
          onChange={(e) =>
            setForm((f) => ({
              ...f,
              size_contracts: Number(e.target.value),
            }))
          }
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Entry Price
        </span>
        <input
          type="number"
          step="0.001"
          min={0}
          className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2 tabular-nums"
          value={form.entry_price}
          onChange={(e) =>
            setForm((f) => ({ ...f, entry_price: Number(e.target.value) }))
          }
        />
      </label>

      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
            Stop
          </span>
          <input
            type="number"
            step="0.001"
            className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2 tabular-nums"
            value={form.stop_loss}
            onChange={(e) =>
              setForm((f) => ({ ...f, stop_loss: e.target.value }))
            }
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
            Take
          </span>
          <input
            type="number"
            step="0.001"
            className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2 tabular-nums"
            value={form.take_profit}
            onChange={(e) =>
              setForm((f) => ({ ...f, take_profit: e.target.value }))
            }
          />
        </label>
      </div>

      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Rationale
        </span>
        <textarea
          className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2 min-h-[48px]"
          placeholder="Why this trade?"
          value={form.rationale}
          onChange={(e) =>
            setForm((f) => ({ ...f, rationale: e.target.value }))
          }
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] text-ink-3 uppercase tracking-widest">
          Linked Journal Entry
        </span>
        <select
          className="bg-surface-2 border border-line-1 px-2 py-1 font-mono text-xs text-ink-2"
          value={form.journal_ref}
          onChange={(e) =>
            setForm((f) => ({ ...f, journal_ref: e.target.value }))
          }
        >
          <option value="">None</option>
          {journalEntries.map((j) => (
            <option key={j.id} value={j.id}>
              {j.hypothesis.slice(0, 60)}
            </option>
          ))}
        </select>
      </label>

      <button
        type="submit"
        disabled={!valid || mutation.isPending}
        className="border border-accent text-accent font-mono text-xs uppercase tracking-widest py-1.5 disabled:border-line-1 disabled:text-ink-4 disabled:cursor-not-allowed"
        data-testid="open-trade-submit"
      >
        {mutation.isPending ? "Opening…" : "Open Trade"}
      </button>

      {errorMsg && <p className="text-xs text-down font-mono">{errorMsg}</p>}
    </form>
  );
}
