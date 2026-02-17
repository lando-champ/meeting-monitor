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
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useEducation } from "@/context/EducationContext";

interface MeetingDetailsProps {
  role: "teacher" | "student";
}

const MeetingDetails = ({ role }: MeetingDetailsProps) => {
  const { classId, lectureId } = useParams();
  const navigate = useNavigate();
  const { getLectureById } = useEducation();
  const lecture = lectureId ? getLectureById(lectureId) : undefined;

  const basePath =
    role === "teacher"
      ? `/education/teacher/classes/${classId}`
      : `/education/student/classes/${classId}`;

  if (!lecture) {
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
        <Button variant="ghost" onClick={() => navigate(basePath + "/dashboard")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        {lecture.meetingLink && (
          <Button
            onClick={() =>
              window.open(lecture.meetingLink, "_blank", "noopener,noreferrer")
            }
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Join Meeting
          </Button>
        )}
      </div>

      <div>
        <h1 className="text-2xl font-bold">{lecture.title}</h1>
        <p className="text-muted-foreground">
          {lecture.className} • {lecture.date} at {lecture.time}
        </p>
        {lecture.description && (
          <p className="text-sm text-muted-foreground mt-2">{lecture.description}</p>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Meeting Transcript */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Meeting Transcript
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Full transcription of the meeting
            </p>
          </CardHeader>
          <CardContent>
            {lecture.transcript && lecture.transcript.length > 0 ? (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {lecture.transcript.map((entry, i) => (
                  <div key={i} className="flex gap-3 text-sm">
                    <span className="font-medium text-muted-foreground min-w-[100px]">
                      {entry.speaker}:
                    </span>
                    <span className="flex-1">{entry.text}</span>
                    <span className="text-xs text-muted-foreground">
                      {entry.timestamp}
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

        {/* Summary (Notes) */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-secondary" />
              Summary & Notes
            </CardTitle>
          </CardHeader>
          <CardContent>
            {lecture.summary ? (
              <div className="space-y-4">
                <p className="text-sm">{lecture.summary.overview}</p>
                {lecture.summary.keyPoints?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      Key Points
                    </p>
                    <ul className="text-sm space-y-1 list-disc list-inside">
                      {lecture.summary.keyPoints.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {lecture.notes && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      Additional Notes
                    </p>
                    <p className="text-sm whitespace-pre-wrap">{lecture.notes}</p>
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

        {/* Attendance with Time */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Attendance
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Members in the meet with join time
            </p>
          </CardHeader>
          <CardContent>
            {lecture.attendance && lecture.attendance.length > 0 ? (
              <ul className="space-y-2">
                {lecture.attendance.map((member) => (
                  <li
                    key={member.id}
                    className="flex items-center justify-between text-sm py-2 border-b last:border-0"
                  >
                    <div>
                      <span className="font-medium">{member.name}</span>
                      <span className="text-muted-foreground text-xs block">
                        {member.email}
                      </span>
                    </div>
                    {member.joinedAt && (
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span className="text-xs">Joined {member.joinedAt}</span>
                      </div>
                    )}
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

        {/* Tasks Assigned */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckSquare className="h-5 w-5" />
              Tasks Assigned
            </CardTitle>
          </CardHeader>
          <CardContent>
            {lecture.tasks && lecture.tasks.length > 0 ? (
              <div className="space-y-3">
                {lecture.tasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center justify-between p-3 rounded-lg border"
                  >
                    <span className="font-medium text-sm">{task.title}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {task.assignee}
                      </Badge>
                      <Badge variant="secondary" className="text-xs capitalize">
                        {task.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No tasks assigned.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Assignments */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5" />
              Assignments
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Assignments from this lecture are available in the Assignments / To-Do
              section. Submit your work before the due date.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MeetingDetails;
