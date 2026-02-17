import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  Users,
  ClipboardList,
  CheckSquare,
  Sparkles,
  MessageSquare,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useEducation } from "@/context/EducationContext";

const LectureSummary = () => {
  const { classId, lectureId } = useParams();
  const navigate = useNavigate();
  const { getLectureById } = useEducation();
  const lecture = lectureId ? getLectureById(lectureId) : undefined;

  if (!lecture) {
    return (
      <div className="p-8">
        <Button variant="ghost" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <p className="mt-4 text-muted-foreground">Lecture not found.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <Button
        variant="ghost"
        onClick={() =>
          navigate(`/education/teacher/classes/${classId}/lecture`)
        }
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Lectures
      </Button>

      <div>
        <h1 className="text-2xl font-bold">{lecture.title}</h1>
        <p className="text-muted-foreground">
          {lecture.className} • {lecture.date} at {lecture.time}
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Transcript */}
        {lecture.transcript && lecture.transcript.length > 0 && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Meeting Transcript
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-48 overflow-y-auto">
                {lecture.transcript.map((entry, i) => (
                  <div key={i} className="flex gap-3 text-sm">
                    <span className="font-medium text-muted-foreground min-w-[100px]">
                      {entry.speaker}:
                    </span>
                    <span className="flex-1">{entry.text}</span>
                    <span className="text-xs text-muted-foreground">{entry.timestamp}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Notes */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Notes
            </CardTitle>
          </CardHeader>
          <CardContent>
            {lecture.notes ? (
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {lecture.notes}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No notes recorded for this lecture.
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
                {lecture.summary.actionItems?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      Action Items
                    </p>
                    <ul className="text-sm space-y-1 list-disc list-inside">
                      {lecture.summary.actionItems.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No AI summary available.
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
              Assignments from this lecture appear in the Assignments tab. Use
              the Create Assignment button to add new ones.
            </p>
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
              List of all members in the meet
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
                      <span className="text-muted-foreground text-xs block">{member.email}</span>
                    </div>
                    {member.joinedAt && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Joined {member.joinedAt}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No attendance data recorded.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Task Assigned */}
        <Card className="md:col-span-2">
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
                    <span className="font-medium">{task.title}</span>
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
                No tasks assigned for this lecture.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default LectureSummary;
