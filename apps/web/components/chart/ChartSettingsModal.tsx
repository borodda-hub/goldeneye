"use client";

import {
  CHART_THEMES,
  type ChartStyle,
  DEFAULT_CHART_STYLE,
} from "@/lib/chart/chartStyle";
import { useEffect } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  style: ChartStyle;
  onChange: (style: ChartStyle) => void;
}

const CROSSHAIR_STYLES: { value: number; label: string }[] = [
  { value: 0, label: "Solid" },
  { value: 2, label: "Dashed" },
  { value: 1, label: "Dotted" },
];

const FONT_SIZES = [9, 10, 11, 12, 13, 14];

function ColorRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-3 py-1">
      <span className="text-xs text-ink-2">{label}</span>
      <span className="flex items-center gap-2">
        <span className="font-mono text-[10px] text-ink-4 tabular-nums">
          {value}
        </span>
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-5 w-7 cursor-pointer rounded border border-line-1 bg-transparent p-0"
          aria-label={label}
        />
      </span>
    </label>
  );
}

function ToggleRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-1">
      <span className="text-xs text-ink-2">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        aria-label={label}
        onClick={() => onChange(!value)}
        className={`relative h-4 w-7 rounded-full transition-colors ${
          value ? "bg-accent" : "bg-surface-3"
        }`}
      >
        <span
          className={`absolute top-0.5 h-3 w-3 rounded-full bg-bg transition-transform ${
            value ? "translate-x-3.5" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border-t border-line-1 pt-2">
      <h3 className="font-mono text-[10px] text-accent uppercase tracking-widest mb-1">
        {title}
      </h3>
      {children}
    </div>
  );
}

export function ChartSettingsModal({ open, onClose, style, onChange }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  // Field edits mark the style "custom"; theme buttons swap the whole preset.
  const set = (partial: Partial<ChartStyle>) =>
    onChange({ ...style, ...partial, theme: "custom" });

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16">
      <button
        type="button"
        aria-label="Close chart settings"
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />
      {/* biome-ignore lint/a11y/useSemanticElements: custom-positioned overlay modal; a native <dialog> would require showModal() and conflict with the backdrop button + Escape handling managed here (matches WalkthroughOverlay) */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Chart appearance settings"
        className="relative w-80 max-h-[80vh] overflow-y-auto rounded-md border border-line-2 bg-surface-1 p-4 shadow-2xl"
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-mono text-[11px] text-ink-1 uppercase tracking-widest">
            Chart Appearance
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-ink-4 hover:text-ink-1 text-sm leading-none"
          >
            ✕
          </button>
        </div>

        {/* Theme presets */}
        <div className="flex items-center gap-1.5 mb-3">
          {(["dark", "light", "gold"] as const).map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => onChange(CHART_THEMES[name])}
              className={`flex-1 rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-widest transition-colors ${
                style.theme === name
                  ? "border-accent text-accent bg-accent-soft"
                  : "border-line-1 text-ink-3 hover:text-ink-1 hover:bg-surface-2"
              }`}
            >
              {name}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-2">
          <Section title="Candles">
            <ColorRow
              label="Up"
              value={style.upColor}
              onChange={(v) => set({ upColor: v })}
            />
            <ColorRow
              label="Down"
              value={style.downColor}
              onChange={(v) => set({ downColor: v })}
            />
            <ColorRow
              label="Wick up"
              value={style.wickUpColor}
              onChange={(v) => set({ wickUpColor: v })}
            />
            <ColorRow
              label="Wick down"
              value={style.wickDownColor}
              onChange={(v) => set({ wickDownColor: v })}
            />
            <ToggleRow
              label="Borders"
              value={style.borderVisible}
              onChange={(v) => set({ borderVisible: v })}
            />
            <ToggleRow
              label="Hollow up-candles"
              value={style.hollowUp}
              onChange={(v) => set({ hollowUp: v })}
            />
          </Section>

          <Section title="Background">
            <ColorRow
              label="Color"
              value={style.background}
              onChange={(v) => set({ background: v })}
            />
            <ToggleRow
              label="Gradient"
              value={style.gradient}
              onChange={(v) => set({ gradient: v })}
            />
            {style.gradient && (
              <ColorRow
                label="Bottom"
                value={style.backgroundBottom}
                onChange={(v) => set({ backgroundBottom: v })}
              />
            )}
          </Section>

          <Section title="Grid">
            <ColorRow
              label="Color"
              value={style.gridColor}
              onChange={(v) => set({ gridColor: v })}
            />
            <ToggleRow
              label="Show grid"
              value={style.gridVisible}
              onChange={(v) => set({ gridVisible: v })}
            />
          </Section>

          <Section title="Crosshair">
            <ColorRow
              label="Color"
              value={style.crosshairColor}
              onChange={(v) => set({ crosshairColor: v })}
            />
            <label className="flex items-center justify-between gap-3 py-1">
              <span className="text-xs text-ink-2">Style</span>
              <select
                value={style.crosshairStyle}
                onChange={(e) =>
                  set({ crosshairStyle: Number(e.target.value) })
                }
                className="rounded border border-line-1 bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-ink-2"
              >
                {CROSSHAIR_STYLES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <ToggleRow
              label="Magnet (snap to bars)"
              value={style.crosshairMagnet}
              onChange={(v) => set({ crosshairMagnet: v })}
            />
          </Section>

          <Section title="Text">
            <ColorRow
              label="Color"
              value={style.textColor}
              onChange={(v) => set({ textColor: v })}
            />
            <label className="flex items-center justify-between gap-3 py-1">
              <span className="text-xs text-ink-2">Size</span>
              <select
                value={style.fontSize}
                onChange={(e) => set({ fontSize: Number(e.target.value) })}
                className="rounded border border-line-1 bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-ink-2"
              >
                {FONT_SIZES.map((s) => (
                  <option key={s} value={s}>
                    {s}px
                  </option>
                ))}
              </select>
            </label>
          </Section>
        </div>

        <button
          type="button"
          onClick={() => onChange(DEFAULT_CHART_STYLE)}
          className="mt-3 w-full rounded border border-line-1 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-ink-3 hover:text-ink-1 hover:bg-surface-2"
        >
          Reset to default
        </button>
      </div>
    </div>
  );
}
