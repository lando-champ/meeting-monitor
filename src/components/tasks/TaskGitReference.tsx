import { Copy, Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { TaskGitEvidenceEntry } from "@/lib/types";

interface TaskGitReferenceProps {
  taskKey?: string | null;
  gitEvidence?: TaskGitEvidenceEntry[] | null;
  variant: "card" | "dialog";
  /** Current title for “Copy for commit” in dialog (e.g. controlled input value). */
  commitTitle?: string;
}

export function TaskGitReference({
  taskKey,
  gitEvidence,
  variant,
  commitTitle = "",
}: TaskGitReferenceProps) {
  const key = (taskKey || "").trim();

  const copyText = (text: string) => {
    void navigator.clipboard.writeText(text);
  };

  if (variant === "card") {
    if (!key) return null;
    return (
      <div
        className="flex items-center gap-1 mt-1.5 pt-1 border-t border-border/60"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <Github className="h-3 w-3 text-muted-foreground shrink-0" aria-hidden />
        <code className="text-[10px] font-mono truncate flex-1 min-w-0">{key}</code>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 shrink-0"
          onClick={(e) => {
            e.stopPropagation();
            copyText(key);
          }}
          aria-label="Copy task key"
        >
          <Copy className="h-3 w-3" />
        </Button>
      </div>
    );
  }

  return (
    <div className="rounded-md border bg-muted/40 px-3 py-2 space-y-2">
      <p className="font-medium text-foreground text-xs flex items-center gap-1.5">
        <Github className="h-3.5 w-3.5" aria-hidden />
        Git integration
      </p>
      {key ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <code className="text-xs font-mono bg-background px-2 py-1 rounded border">{key}</code>
            <Button type="button" variant="secondary" size="sm" className="h-7 text-xs" onClick={() => copyText(key)}>
              Copy key
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => {
                const line = `${key}: ${(commitTitle || "").trim()}`.trim();
                copyText(line);
              }}
            >
              Copy for commit
            </Button>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Put this key in a merged pull request title or description so the task moves to Done when the PR merges.
          </p>
        </>
      ) : (
        <p className="text-xs text-muted-foreground">Task key appears after the board loads or syncs from meetings.</p>
      )}
      {gitEvidence && gitEvidence.length > 0 && (
        <div>
          <p className="text-xs font-medium text-foreground mb-1">Recent Git activity</p>
          <ul className="text-xs space-y-1 max-h-28 overflow-y-auto border rounded-md bg-background/50 p-2">
            {[...gitEvidence].reverse().slice(0, 5).map((ev, i) => (
              <li key={i} className="text-muted-foreground break-words">
                {ev.url ? (
                  <a href={ev.url} target="_blank" rel="noreferrer" className="text-primary underline">
                    Link
                  </a>
                ) : null}
                {ev.url ? " · " : null}
                {ev.message || ev.event || "event"}
                {ev.actor ? ` — ${ev.actor}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
