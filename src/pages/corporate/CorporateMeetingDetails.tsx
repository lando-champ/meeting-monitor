import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  Users,
  ClipboardList,
  CheckSquare,
  Sparkles,
  MessageSquare,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { mockMeetings } from "@/data/mockData";
import { loadWorkspaceMeetings } from "@/lib/workspaceStorage";
import { format } from "date-fns";
import { Meeting } from "@/lib/types";

interface CorporateMeetingDetailsProps {
  role: "manager" | "member";
}

const CorporateMeetingDetails = ({ role }: CorporateMeetingDetailsProps) => {
  const { workspaceId, meetingId } = useParams();
  const navigate = useNavigate();

  const scheduledFromStorage = loadWorkspaceMeetings(workspaceId || "alpha", []);
  const allMeetings = [
    ...mockMeetings,
    ...scheduledFromStorage.filter(
      (m) => !mockMeetings.some((mm) => mm.id === m.id)
    ),
  ];
  const meeting = meetingId
    ? allMeetings.find((m) => m.id === meetingId)
    : undefined;

  const basePath =
    role === "manager"
      ? `/business/manager/workspaces/${workspaceId}`
      : `/business/member/workspaces/${workspaceId}`;

  if (!meeting) {
    return (
      <div className="p-8">
        <Button variant="ghost" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <p className="mt-4 text-muted-foreground">Meeting not found.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate(`${basePath}/dashboard`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        {meeting.meetingLink && (
          <Button
            onClick={() =>
              window.open(meeting.meetingLink, "_blank", "noopener,noreferrer")
            }
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Join Meeting
          </Button>
        )}
      </div>

      <div>
        <h1 className="text-2xl font-bold">{meeting.title}</h1>
        <p className="text-muted-foreground">
          {format(meeting.startTime, "MMMM d, yyyy • h:mm a")} • {meeting.status}
        </p>
        {meeting.description && (
          <p className="text-sm text-muted-foreground mt-2">
            {meeting.description}
          </p>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Transcript */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Meeting Transcript
            </CardTitle>
          </CardHeader>
          <CardContent>
            {meeting.transcript && meeting.transcript.length > 0 ? (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {meeting.transcript.map((entry) => (
                  <div key={entry.id} className="flex gap-3 text-sm">
                    <span className="font-medium text-muted-foreground min-w-[120px]">
                      {entry.speaker.name}:
                    </span>
                    <span className="flex-1">{entry.text}</span>
                    <span className="text-xs text-muted-foreground">
                      {format(entry.timestamp, "h:mm")}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No transcript available.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-secondary" />
              Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            {meeting.summary ? (
              <div className="space-y-4">
                <p className="text-sm">{meeting.summary.overview}</p>
                {meeting.summary.keyPoints?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      Key Points
                    </p>
                    <ul className="text-sm space-y-1 list-disc list-inside">
                      {meeting.summary.keyPoints.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {meeting.summary.decisions?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      Decisions
                    </p>
                    <ul className="text-sm space-y-1 list-disc list-inside">
                      {meeting.summary.decisions.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No summary available.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Attendance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Attendance
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              List of all members in the meeting
            </p>
          </CardHeader>
          <CardContent>
            {meeting.participants && meeting.participants.length > 0 ? (
              <ul className="space-y-2">
                {meeting.participants.map((p) => (
                  <li
                    key={p.id}
                    className="flex items-center justify-between text-sm py-2 border-b last:border-0"
                  >
                    <span className="font-medium">{p.name}</span>
                    <span className="text-muted-foreground text-xs">
                      {p.email}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No attendance data.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Tasks / Action Items */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckSquare className="h-5 w-5" />
              Tasks & Action Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            {meeting.summary?.actionItems && meeting.summary.actionItems.length > 0 ? (
              <div className="space-y-3">
                {meeting.summary.actionItems.map((item, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 p-3 rounded-lg border"
                  >
                    <CheckSquare className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{item}</span>
                  </div>
                ))}
              </div>
            ) : meeting.actionItems && meeting.actionItems.length > 0 ? (
              <div className="space-y-3">
                {meeting.actionItems.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center justify-between p-3 rounded-lg border"
                  >
                    <span className="font-medium text-sm">{task.title}</span>
                    <Badge variant="secondary" className="text-xs capitalize">
                      {task.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No tasks or action items.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CorporateMeetingDetails;
