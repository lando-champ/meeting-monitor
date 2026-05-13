import { useEffect, useRef, useState } from "react";
import { getWsBaseUrl } from "@/lib/api";

interface Line {
  id: number;
  text: string;
}

const MAX_LINES = 400;
const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30_000;

interface ServerLiveMeetingTranscriptProps {
  meetingId: string;
  /** When false, disconnect and clear (e.g. meeting ended). */
  enabled: boolean;
  accessToken: string | null;
  className?: string;
}

/**
 * Subscribes to backend STT stream: `WS /api/v1/ws/meeting/{id}/live`.
 * Sends a periodic ping (receive_text loop) to keep the connection alive.
 */
export default function ServerLiveMeetingTranscript({
  meetingId,
  enabled,
  accessToken,
  className = "",
}: ServerLiveMeetingTranscriptProps) {
  const [lines, setLines] = useState<Line[]>([]);
  const [status, setStatus] = useState<"idle" | "connecting" | "live" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(0);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffRef = useRef(INITIAL_BACKOFF_MS);
  const shouldRunRef = useRef(false);

  const clearReconnect = () => {
    if (reconnectTimerRef.current != null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  };

  useEffect(() => {
    shouldRunRef.current = Boolean(enabled && meetingId);
    if (!shouldRunRef.current) {
      clearReconnect();
      wsRef.current?.close();
      wsRef.current = null;
      setStatus("idle");
      return;
    }

    const connect = () => {
      if (!shouldRunRef.current) return;
      const base = getWsBaseUrl();
      const q = accessToken ? `?access_token=${encodeURIComponent(accessToken)}` : "";
      const url = `${base}/api/v1/ws/meeting/${encodeURIComponent(meetingId)}/live${q}`;
      setStatus("connecting");
      setError(null);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        backoffRef.current = INITIAL_BACKOFF_MS;
        setStatus("live");
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(String(ev.data)) as { type?: string; text?: string };
          if (data.type === "transcript" && (data.text || "").trim()) {
            const t = data.text!.trim();
            idRef.current += 1;
            setLines((prev) => {
              const next = [...prev, { id: idRef.current, text: t }];
              return next.length > MAX_LINES ? next.slice(-MAX_LINES) : next;
            });
          }
        } catch {
          /* ignore non-JSON */
        }
      };

      ws.onerror = () => {
        setError("WebSocket error");
        setStatus("error");
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (!shouldRunRef.current) return;
        setStatus("connecting");
        const delay = Math.min(MAX_BACKOFF_MS, backoffRef.current);
        backoffRef.current = Math.min(MAX_BACKOFF_MS, backoffRef.current * 2);
        clearReconnect();
        reconnectTimerRef.current = window.setTimeout(connect, delay);
      };
    };

    connect();

    const ping = window.setInterval(() => {
      const w = wsRef.current;
      if (w && w.readyState === WebSocket.OPEN) {
        try {
          w.send("ping");
        } catch {
          /* ignore */
        }
      }
    }, 25_000);

    return () => {
      shouldRunRef.current = false;
      clearReconnect();
      clearInterval(ping);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [enabled, meetingId, accessToken]);

  if (!enabled) {
    return null;
  }

  return (
    <div className={className}>
      <p className="text-xs text-muted-foreground mb-2">
        Server live transcript (meeting bot / Groq or local STT). Reconnects automatically if the connection drops.
      </p>
      {error && <p className="text-xs text-destructive mb-2">{error}</p>}
      <p className="text-xs text-muted-foreground mb-2 capitalize">Status: {status}</p>
      <div className="max-h-64 overflow-y-auto rounded border bg-muted/30 p-3 text-sm space-y-2">
        {lines.length === 0 && status !== "live" && (
          <p className="text-muted-foreground italic">Connecting to live stream…</p>
        )}
        {lines.length === 0 && status === "live" && (
          <p className="text-muted-foreground italic">Waiting for speech from the meeting…</p>
        )}
        {lines.map((row) => (
          <p key={row.id} className="border-l-2 border-emerald-600/50 pl-2">
            {row.text}
          </p>
        ))}
      </div>
    </div>
  );
}
