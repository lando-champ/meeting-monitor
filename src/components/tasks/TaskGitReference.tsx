import { Copy, ExternalLink, Github } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { TaskGitEvidenceEntry } from "@/lib/types";

interface TaskGitReferenceProps {
  taskKey?: string | null;
  gitEvidence?: TaskGitEvidenceEntry[] | null;
  variant: "card" | "dialog";
  /** Current title for “Copy for commit” in dialog (e.g. controlled input value). */
  commitTitle?: string;
  /** Latest GitHub Actions workflow_run conclusion for this task (from API). */
  githubCiConclusion?: string | null;
  githubCiUpdatedAt?: string | null;
  githubCiWorkflowUrl?: string | null;
  githubCiHeadSha?: string | null;
}

function ciBadgeClass(conclusion: string): string {
  const c = conclusion.toLowerCase();
  if (c === "success")
    return "bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200/80";
  if (c === "failure")
    return "bg-destructive/15 text-destructive dark:bg-destructive/25 border-destructive/30";
  if (c === "cancelled" || c === "skipped")
    return "bg-muted text-muted-foreground border-border";
  return "bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200 border-amber-200/60";
}

export function TaskGitReference({
  taskKey,
  gitEvidence,
  variant,
  commitTitle = "",
  githubCiConclusion,
  githubCiUpdatedAt,
  githubCiWorkflowUrl,
  githubCiHeadSha,
}: TaskGitReferenceProps) {
  const key = (taskKey || "").trim();
  const ci = (githubCiConclusion || "").trim().toLowerCase();
  const hasCi = Boolean(ci);
  const ciTime =
    githubCiUpdatedAt && !Number.isNaN(Date.parse(githubCiUpdatedAt))
      ? formatDistanceToNow(new Date(githubCiUpdatedAt), { addSuffix: true })
      : null;

  const copyText = (text: string) => {
    void navigator.clipboard.writeText(text);
  };

  if (variant === "card") {
    if (!key && !hasCi) return null;
    return (
      <div
        className="mt-1.5 pt-1 border-t border-border/60 space-y-1"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        {key ? (
          <div className="flex items-center gap-1">
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
        ) : null}
        {hasCi ? (
          <div className="flex items-center gap-1.5 flex-wrap">
            <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0 font-normal", ciBadgeClass(ci))}>
              CI: {githubCiConclusion}
            </Badge>
            {ciTime ? <span className="text-[10px] text-muted-foreground">{ciTime}</span> : null}
            {githubCiWorkflowUrl ? (
              <a
                href={githubCiWorkflowUrl}
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-primary inline-flex items-center gap-0.5 shrink-0"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="h-2.5 w-2.5" />
                Run
              </a>
            ) : null}
          </div>
        ) : null}
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
            Put this key in a merged pull request title or description. With CI gating enabled on the server, the task
            moves to Done only after Actions reports success for that PR; failed runs can move the task to Blockers.
          </p>
        </>
      ) : (
        <p className="text-xs text-muted-foreground">Task key appears after the board loads or syncs from meetings.</p>
      )}
      {hasCi ? (
        <div className="rounded-md border bg-background/60 px-2 py-2 space-y-1.5">
          <p className="text-xs font-medium text-foreground">GitHub Actions (last workflow for this task)</p>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className={cn("text-xs font-normal", ciBadgeClass(ci))}>
              {githubCiConclusion}
            </Badge>
            {ciTime ? <span className="text-xs text-muted-foreground">Updated {ciTime}</span> : null}
          </div>
          {githubCiHeadSha ? (
            <p className="text-xs text-muted-foreground font-mono break-all">PR head: {githubCiHeadSha.slice(0, 7)}…</p>
          ) : null}
          {githubCiWorkflowUrl ? (
            <a
              href={githubCiWorkflowUrl}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-primary inline-flex items-center gap-1"
            >
              <ExternalLink className="h-3 w-3" />
              Open workflow run on GitHub
            </a>
          ) : null}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          No CI run recorded yet for this task. After you enable the{" "}
          <code className="rounded bg-muted px-1">workflow_run</code> webhook and link the repo, results appear here.
        </p>
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
