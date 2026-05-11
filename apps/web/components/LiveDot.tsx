interface Props {
  connected: boolean;
}

export function LiveDot({ connected }: Props) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${
        connected ? "bg-up animate-pulse" : "bg-down"
      }`}
      aria-label={connected ? "Connected" : "Disconnected"}
    />
  );
}
