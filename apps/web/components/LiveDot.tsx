interface Props {
  connected: boolean;
  /**
   * Feed mode:
   *  - "live"    — real-time feed; dot pulses green when connected
   *  - "delayed" — delayed feed (e.g. ~15 min via Yahoo). Amber dot, no pulse,
   *                because the data is real but the heartbeat is not real-time.
   */
  mode?: "live" | "delayed";
}

export function LiveDot({ connected, mode = "live" }: Props) {
  if (!connected) {
    return (
      <span
        className="inline-block w-2 h-2 rounded-full bg-down"
        aria-label="Disconnected"
      />
    );
  }
  if (mode === "delayed") {
    return (
      <span
        className="inline-block w-2 h-2 rounded-full bg-conf-medium"
        aria-label="Connected (delayed feed)"
      />
    );
  }
  return (
    <span
      className="inline-block w-2 h-2 rounded-full bg-up animate-pulse"
      aria-label="Connected"
    />
  );
}
