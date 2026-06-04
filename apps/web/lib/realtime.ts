"use client";

import { useEffect, useRef, useState } from "react";

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";

const WS_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_WS_BASE ??
      (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000").replace(
        /^http/,
        "ws",
      ))
    : "ws://localhost:8000";

const HEARTBEAT_INTERVAL = 30_000;
const BASE_RECONNECT_MS = 1_000;
const MAX_RECONNECT_MS = 30_000;

type Listener<T> = (data: T) => void;

class RealtimeClient {
  private ws: WebSocket | null = null;
  private listeners = new Map<string, Set<Listener<unknown>>>();
  private status: ConnectionStatus = "disconnected";
  private statusListeners = new Set<(s: ConnectionStatus) => void>();
  private reconnectAttempt = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private destroyed = false;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.setStatus("connecting");
    try {
      this.ws = new WebSocket(`${WS_BASE}/ws`);
    } catch {
      this.setStatus("error");
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempt = 0;
      this.setStatus("connected");
      this.startHeartbeat();
      // Re-subscribe to all channels
      for (const channel of this.listeners.keys()) {
        this.sendSubscribe(channel);
      }
    };

    this.ws.onmessage = (evt: MessageEvent) => {
      try {
        const msg = JSON.parse(evt.data as string) as {
          op?: string;
          channel?: string;
          data?: unknown;
        };
        if (msg.op === "pong") return;
        if (msg.channel && msg.data !== undefined) {
          const subs = this.listeners.get(msg.channel);
          if (subs) {
            for (const fn of subs) fn(msg.data);
          }
        }
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onerror = () => {
      this.setStatus("error");
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
      if (!this.destroyed) {
        this.setStatus("disconnected");
        this.scheduleReconnect();
      }
    };
  }

  private sendSubscribe(channel: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ op: "subscribe", channel }));
    }
  }

  private sendUnsubscribe(channel: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ op: "unsubscribe", channel }));
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ op: "ping" }));
      }
    }, HEARTBEAT_INTERVAL);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect() {
    if (this.destroyed) return;
    const delay = Math.min(
      BASE_RECONNECT_MS * 2 ** this.reconnectAttempt,
      MAX_RECONNECT_MS,
    );
    this.reconnectAttempt += 1;
    this.reconnectTimer = setTimeout(() => {
      if (!this.destroyed) this.connect();
    }, delay);
  }

  private setStatus(s: ConnectionStatus) {
    this.status = s;
    for (const fn of this.statusListeners) fn(s);
  }

  subscribe<T>(channel: string, listener: Listener<T>) {
    let set = this.listeners.get(channel);
    if (!set) {
      set = new Set();
      this.listeners.set(channel, set);
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendSubscribe(channel);
      }
    }
    set.add(listener as Listener<unknown>);

    if (this.ws === null) {
      this.connect();
    }
  }

  unsubscribe<T>(channel: string, listener: Listener<T>) {
    const subs = this.listeners.get(channel);
    if (!subs) return;
    subs.delete(listener as Listener<unknown>);
    if (subs.size === 0) {
      this.listeners.delete(channel);
      this.sendUnsubscribe(channel);
    }
  }

  onStatusChange(fn: (s: ConnectionStatus) => void) {
    this.statusListeners.add(fn);
    return () => this.statusListeners.delete(fn);
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  destroy() {
    this.destroyed = true;
    this.stopHeartbeat();
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
    }
    this.ws?.close();
  }
}

let singleton: RealtimeClient | null = null;

function getClient(): RealtimeClient {
  if (!singleton) {
    singleton = new RealtimeClient();
  }
  return singleton;
}

export function useChannel<T>(channel: string): {
  data: T | null;
  status: ConnectionStatus;
} {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const clientRef = useRef<RealtimeClient | null>(null);

  useEffect(() => {
    const client = getClient();
    clientRef.current = client;

    setStatus(client.getStatus());

    const listener = (d: T) => setData(d);
    client.subscribe<T>(channel, listener);
    const unsubStatus = client.onStatusChange(setStatus);

    return () => {
      client.unsubscribe<T>(channel, listener);
      unsubStatus();
    };
  }, [channel]);

  return { data, status };
}
