import {
  useEffect,
  useState,
  useRef,
  useCallback,
  forwardRef,
  useImperativeHandle,
} from "react";
import { Button } from "@/components/ui/button";
import { Mic, MicOff } from "lucide-react";

export interface LiveMeetingTranscriptRef {
  /** Final lines plus any current interim text (for saving before ending the meeting). */
  collectTextsForSave: () => string[];
}

interface LiveMeetingTranscriptProps {
  meetingId?: string;
  className?: string;
}

interface TranscriptLine {
  id: string;
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

const RESTART_MS = 80;
const NETWORK_RETRY_CAP = 5;

/**
 * Browser-only live transcription via Web Speech API (no server WebSocket).
 * Use ref.collectTextsForSave() before ending the meeting to persist lines via the API.
 */
const LiveMeetingTranscript = forwardRef<LiveMeetingTranscriptRef, LiveMeetingTranscriptProps>(
  function LiveMeetingTranscript({ className = "" }, ref) {
    const [lines, setLines] = useState<TranscriptLine[]>([]);
    const [micOn, setMicOn] = useState(false);
    const [interimBrowser, setInterimBrowser] = useState("");
    const [speechError, setSpeechError] = useState<string | null>(null);
    const recognitionRef = useRef<SpeechRecognition | null>(null);
    const micStreamRef = useRef<MediaStream | null>(null);
    const listeningIntentRef = useRef(false);
    const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const networkFailCountRef = useRef(0);
    const lineIdRef = useRef(0);
    /** Mirrors final lines for imperative read (must stay in sync with displayed finals). */
    const linesTextRef = useRef<string[]>([]);
    const interimTextRef = useRef("");

    const nextId = () => {
      lineIdRef.current += 1;
      return `l-${lineIdRef.current}`;
    };

    const clearRestartTimer = () => {
      if (restartTimerRef.current != null) {
        clearTimeout(restartTimerRef.current);
        restartTimerRef.current = null;
      }
    };

    useImperativeHandle(ref, () => ({
      collectTextsForSave: () => {
        const interim = interimTextRef.current.trim();
        const base = [...linesTextRef.current];
        return interim ? [...base, interim] : base;
      },
    }));

    const scheduleRestart = useCallback((recognition: SpeechRecognition) => {
      clearRestartTimer();
      restartTimerRef.current = setTimeout(() => {
        restartTimerRef.current = null;
        if (!listeningIntentRef.current) return;
        try {
          recognition.start();
          networkFailCountRef.current = 0;
        } catch {
          if (listeningIntentRef.current) {
            restartTimerRef.current = setTimeout(() => {
              restartTimerRef.current = null;
              if (!listeningIntentRef.current) return;
              try {
                recognition.start();
              } catch {
                /* ignore */
              }
            }, 200);
          }
        }
      }, RESTART_MS);
    }, []);

    const stopBrowserMic = useCallback(() => {
      listeningIntentRef.current = false;
      clearRestartTimer();
      setMicOn(false);
      setInterimBrowser("");
      interimTextRef.current = "";
      setSpeechError(null);
      networkFailCountRef.current = 0;
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
      networkFailCountRef.current = 0;

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
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
        setSpeechError(null);
        let interim = "";
        let finalChunk = "";
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const r = event.results[i];
          const t = r[0]?.transcript ?? "";
          if (r.isFinal) finalChunk += t;
          else interim += t;
        }
        if (finalChunk.trim()) {
          const t = finalChunk.trim();
          linesTextRef.current = [...linesTextRef.current, t];
          setLines((prev) => [...prev, { id: nextId(), text: t }]);
        }
        const interimTrim = interim.trim();
        interimTextRef.current = interimTrim;
        setInterimBrowser(interimTrim);
      };

      recognition.onerror = (ev: SpeechRecognitionErrorEvent) => {
        if (ev.error === "not-allowed") {
          setSpeechError("Microphone or speech recognition was blocked.");
          stopBrowserMic();
          return;
        }
        if (ev.error === "aborted") return;
        if (ev.error === "no-speech") {
          return;
        }
        if (ev.error === "network") {
          networkFailCountRef.current += 1;
          if (networkFailCountRef.current >= NETWORK_RETRY_CAP) {
            setSpeechError("Speech recognition network error. Try stopping and starting the mic again.");
            stopBrowserMic();
            return;
          }
          setSpeechError("Network hiccup — reconnecting…");
          return;
        }
        if (ev.error === "service-not-allowed") {
          setSpeechError("Speech recognition service not allowed in this context.");
          stopBrowserMic();
          return;
        }
        setSpeechError(ev.error || "Speech recognition error");
      };

      recognition.onend = () => {
        if (!listeningIntentRef.current) return;
        scheduleRestart(recognition);
      };

      recognitionRef.current = recognition;
      listeningIntentRef.current = true;
      setMicOn(true);
      try {
        recognition.start();
      } catch {
        listeningIntentRef.current = false;
        setSpeechError("Could not start speech recognition.");
        stopBrowserMic();
      }
    }, [scheduleRestart, stopBrowserMic]);

    useEffect(() => {
      return () => {
        listeningIntentRef.current = false;
        clearRestartTimer();
        stopBrowserMic();
      };
    }, [stopBrowserMic]);

    const speechSupported = typeof window !== "undefined" && !!getSpeechRecognitionCtor();

    return (
      <div className={className}>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {speechSupported ? (
            micOn ? (
              <Button type="button" variant="secondary" size="sm" onClick={stopBrowserMic}>
                <MicOff className="h-4 w-4 mr-2" />
                Stop mic
              </Button>
            ) : (
              <Button type="button" variant="default" size="sm" onClick={startBrowserMic}>
                <Mic className="h-4 w-4 mr-2" />
                Mic (Web Speech)
              </Button>
            )
          ) : (
            <p className="text-xs text-muted-foreground">
              Web Speech API not available (use Chrome or Edge for local transcription).
            </p>
          )}
          {micOn && (
            <span className="text-xs text-amber-700 dark:text-amber-500">Listening in your browser…</span>
          )}
        </div>
        {speechError && <p className="text-xs text-destructive mb-2">{speechError}</p>}

        <p className="text-xs text-muted-foreground mb-2">
          When you click <span className="font-medium">End meeting</span>, your transcript is saved to the server and
          included in the full transcript and summary.
        </p>

        <div className="max-h-64 overflow-y-auto rounded border bg-muted/30 p-3 text-sm space-y-2">
          {!micOn && lines.length === 0 && !interimBrowser && (
            <p className="text-muted-foreground italic">
              Turn on the mic to transcribe in the browser.
            </p>
          )}
          {micOn && lines.length === 0 && !interimBrowser && (
            <p className="text-muted-foreground italic">Speak clearly — words will appear here.</p>
          )}
          {lines.map((row) => (
            <p key={row.id} className="border-l-2 border-primary/40 pl-2">
              {row.text}
            </p>
          ))}
          {interimBrowser && (
            <p className="border-l-2 border-primary/25 pl-2 text-muted-foreground italic">{interimBrowser}</p>
          )}
        </div>
      </div>
    );
  }
);

export default LiveMeetingTranscript;
