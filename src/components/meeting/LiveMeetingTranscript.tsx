import { useEffect, useState, useRef, useCallback } from "react";
import { getWsBaseUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Mic, MicOff } from "lucide-react";

interface LiveMeetingTranscriptProps {
  meetingId: string;
  className?: string;
}

type TranscriptSource = "server" | "browser";

interface TranscriptLine {
  id: string;
  source: TranscriptSource;
  text: string;
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognition) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognition;
    webkitSpeechRecognition?: new () => SpeechRecognition;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

/**
 * Connects to /api/v1/ws/meeting/{meetingId}/live (server STT) and optional browser Web Speech mic.
 */
export default function LiveMeetingTranscript({ meetingId, className = "" }: LiveMeetingTranscriptProps) {
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [connected, setConnected] = useState(false);
  const [micOn, setMicOn] = useState(false);
  const [interimBrowser, setInterimBrowser] = useState("");
  const [speechError, setSpeechError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const micOnRef = useRef(false);
  const lineIdRef = useRef(0);

  const nextId = () => {
    lineIdRef.current += 1;
    return `l-${lineIdRef.current}`;
  };

  useEffect(() => {
    micOnRef.current = micOn;
  }, [micOn]);

  useEffect(() => {
    if (!meetingId) return;
    const base = getWsBaseUrl();
    const url = `${base}/api/v1/ws/meeting/${meetingId}/live`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "transcript" && data.text) {
          setLines((prev) => [...prev, { id: nextId(), source: "server", text: data.text }]);
        }
      } catch {
        // ignore
      }
    };
    ws.onerror = () => setConnected(false);
    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [meetingId]);

  const stopBrowserMic = useCallback(() => {
    setMicOn(false);
    setInterimBrowser("");
    setSpeechError(null);
    try {
      recognitionRef.current?.stop();
    } catch {
      /* ignore */
    }
    recognitionRef.current = null;
    micStreamRef.current?.getTracks().forEach((t) => t.stop());
    micStreamRef.current = null;
  }, []);

  const startBrowserMic = useCallback(async () => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setSpeechError("Web Speech API is not supported in this browser. Try Chrome or Edge.");
      return;
    }
    setSpeechError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
    } catch {
      setSpeechError("Microphone permission denied or unavailable.");
      return;
    }

    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = typeof navigator !== "undefined" ? navigator.language || "en-US" : "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      let finalChunk = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const r = event.results[i];
        const t = r[0]?.transcript ?? "";
        if (r.isFinal) finalChunk += t;
        else interim += t;
      }
      if (finalChunk.trim()) {
        setLines((prev) => [...prev, { id: nextId(), source: "browser", text: finalChunk.trim() }]);
      }
      setInterimBrowser(interim.trim());
    };

    recognition.onerror = (ev: SpeechRecognitionErrorEvent) => {
      if (ev.error === "not-allowed") {
        setSpeechError("Microphone or speech recognition was blocked.");
        stopBrowserMic();
        return;
      }
      if (ev.error === "aborted" || ev.error === "no-speech") return;
      setSpeechError(ev.error || "Speech recognition error");
    };

    recognition.onend = () => {
      if (micOnRef.current) {
        try {
          recognition.start();
        } catch {
          /* may throw if already started */
        }
      }
    };

    recognitionRef.current = recognition;
    setMicOn(true);
    try {
      recognition.start();
    } catch {
      setSpeechError("Could not start speech recognition.");
      stopBrowserMic();
    }
  }, [stopBrowserMic]);

  useEffect(() => {
    return () => {
      stopBrowserMic();
    };
  }, [stopBrowserMic]);

  const speechSupported = typeof window !== "undefined" && !!getSpeechRecognitionCtor();

  return (
    <div className={className}>
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground mb-2">
        <span className={connected ? "text-green-600" : "text-muted-foreground"}>
          {connected ? "● Server live" : "○ Server disconnected"}
        </span>
        <span className="text-muted-foreground/60">|</span>
        <span className="text-xs">Server = Groq STT from the meeting bot (runs on the API host).</span>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-3">
        {speechSupported ? (
          micOn ? (
            <Button type="button" variant="secondary" size="sm" onClick={stopBrowserMic}>
              <MicOff className="h-4 w-4 mr-2" />
              Stop browser mic
            </Button>
          ) : (
            <Button type="button" variant="outline" size="sm" onClick={startBrowserMic}>
              <Mic className="h-4 w-4 mr-2" />
              Mic (browser / Web Speech)
            </Button>
          )
        ) : (
          <p className="text-xs text-muted-foreground">
            Web Speech API not available (use Chrome or Edge for local mic captions).
          </p>
        )}
        {micOn && <span className="text-xs text-amber-700 dark:text-amber-500">Listening in your browser…</span>}
      </div>
      {speechError && <p className="text-xs text-destructive mb-2">{speechError}</p>}

      <div className="max-h-64 overflow-y-auto rounded border bg-muted/30 p-3 text-sm space-y-2">
        {lines.length === 0 && !connected && <p className="text-muted-foreground italic">Connecting to server…</p>}
        {lines.length === 0 && connected && !interimBrowser && (
          <p className="text-muted-foreground italic">Waiting for server transcript…</p>
        )}
        {lines.map((row) => (
          <p
            key={row.id}
            className={
              row.source === "browser"
                ? "border-l-2 border-amber-500/60 pl-2 text-foreground/90"
                : "border-l-2 border-primary/40 pl-2"
            }
          >
            <span className="text-[10px] uppercase tracking-wide text-muted-foreground mr-2">
              {row.source === "server" ? "Server" : "Browser"}
            </span>
            {row.text}
          </p>
        ))}
        {interimBrowser && (
          <p className="border-l-2 border-amber-500/30 pl-2 text-muted-foreground italic">
            <span className="text-[10px] uppercase tracking-wide mr-2">Browser</span>
            {interimBrowser}
          </p>
        )}
      </div>
    </div>
  );
}
