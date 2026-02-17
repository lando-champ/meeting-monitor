import { useState, useCallback } from 'react';
import { 
  Upload, 
  FileAudio, 
  FileVideo, 
  Loader2, 
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  MessageSquare,
  ListTodo,
  FileText,
  Users,
  Clock
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

type ProcessingState = 'idle' | 'uploading' | 'transcribing' | 'analyzing' | 'extracting' | 'complete';

interface ExtractedTask {
  id: string;
  title: string;
  assignee: string;
  deadline: string;
  priority: 'high' | 'medium' | 'low';
}

interface ModerationFlag {
  type: 'off-topic' | 'dominance' | 'interruption';
  speaker: string;
  timestamp: string;
  description: string;
}

interface UploadMeetingProps {
  variant?: 'corporate' | 'education';
  title?: string;
}

const mockTranscript = `
[00:00:15] Sarah Chen: Good morning everyone. Let's start with our sprint planning session.

[00:00:45] Mike Johnson: Thanks Sarah. I wanted to discuss the API integration timeline.

[00:01:20] Sarah Chen: Great point. We need to have this done by Friday. Mike, can you take the lead on this?

[00:01:45] Mike Johnson: Absolutely. I'll coordinate with the backend team.

[00:02:30] Emily Rodriguez: I can help with the frontend components. Should we aim for Wednesday for the initial PR?

[00:03:00] Sarah Chen: That sounds perfect. Let's make sure we have unit tests included.

[00:03:30] Alex Kim: What about the documentation? We should update the API docs as well.

[00:04:00] Sarah Chen: Good catch Alex. Can you own the documentation updates?

[00:04:15] Alex Kim: Sure, I'll have it ready by Thursday.
`;

const mockSummary = {
  overview: "Sprint planning meeting focused on API integration timeline and task assignments. The team discussed deliverables for the upcoming week with clear ownership and deadlines.",
  keyPoints: [
    "API integration is the main priority for this sprint",
    "Frontend components PR targeted for Wednesday",
    "Documentation updates to be completed by Thursday",
    "Unit tests are required for all new code"
  ],
  decisions: [
    "Mike Johnson will lead the API integration effort",
    "Emily Rodriguez to handle frontend components",
    "Alex Kim responsible for documentation updates",
    "Friday is the hard deadline for API integration"
  ]
};

const mockTasks: ExtractedTask[] = [
  { id: '1', title: 'Complete API integration', assignee: 'Mike Johnson', deadline: 'Friday', priority: 'high' },
  { id: '2', title: 'Frontend components PR', assignee: 'Emily Rodriguez', deadline: 'Wednesday', priority: 'high' },
  { id: '3', title: 'Update API documentation', assignee: 'Alex Kim', deadline: 'Thursday', priority: 'medium' },
  { id: '4', title: 'Add unit tests for new code', assignee: 'Team', deadline: 'Friday', priority: 'medium' },
];

const mockModerationFlags: ModerationFlag[] = [
  { type: 'interruption', speaker: 'Mike Johnson', timestamp: '00:02:15', description: 'Interrupted Emily during her suggestion' },
  { type: 'dominance', speaker: 'Sarah Chen', timestamp: 'Overall', description: 'Speaking time 45% - above average' },
];

const processingSteps = [
  { state: 'uploading', label: 'Uploading file...', progress: 20 },
  { state: 'transcribing', label: 'Transcribing audio...', progress: 45 },
  { state: 'analyzing', label: 'Analyzing content...', progress: 70 },
  { state: 'extracting', label: 'Extracting action items...', progress: 90 },
  { state: 'complete', label: 'Processing complete!', progress: 100 },
];

const UploadMeeting = ({ variant = 'corporate', title = 'Upload Meeting Recording' }: UploadMeetingProps) => {
  const [processingState, setProcessingState] = useState<ProcessingState>('idle');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const simulateProcessing = useCallback(() => {
    const states: ProcessingState[] = ['uploading', 'transcribing', 'analyzing', 'extracting', 'complete'];
    let index = 0;

    const interval = setInterval(() => {
      setProcessingState(states[index]);
      index++;
      if (index >= states.length) {
        clearInterval(interval);
      }
    }, 1500);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      setUploadedFile(files[0]);
      simulateProcessing();
    }
  }, [simulateProcessing]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setUploadedFile(files[0]);
      simulateProcessing();
    }
  }, [simulateProcessing]);

  const resetUpload = useCallback(() => {
    setProcessingState('idle');
    setUploadedFile(null);
  }, []);

  const currentStep = processingSteps.find(s => s.state === processingState);

  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {processingState === 'idle' && (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={cn(
              "border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer",
              isDragging 
                ? "border-primary bg-primary/5" 
                : "border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/50"
            )}
          >
            <input
              type="file"
              accept="audio/*,video/*"
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="flex flex-col items-center gap-4">
                <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <Upload className="h-8 w-8 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-lg mb-1">
                    {isDragging ? 'Drop your file here' : 'Drag & drop or click to upload'}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Supports MP3, WAV, M4A, MP4, WebM, and more
                  </p>
                </div>
                <div className="flex items-center gap-4 text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <FileAudio className="h-4 w-4" />
                    <span className="text-sm">Audio</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <FileVideo className="h-4 w-4" />
                    <span className="text-sm">Video</span>
                  </div>
                </div>
              </div>
            </label>
          </div>
        )}

        {processingState !== 'idle' && processingState !== 'complete' && (
          <div className="py-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <Loader2 className="h-6 w-6 text-primary animate-spin" />
              </div>
              <div className="flex-1">
                <p className="font-medium">{currentStep?.label}</p>
                <p className="text-sm text-muted-foreground">{uploadedFile?.name}</p>
              </div>
            </div>
            <Progress value={currentStep?.progress || 0} className="h-2" />
            <div className="flex justify-between mt-2 text-xs text-muted-foreground">
              <span>Processing...</span>
              <span>{currentStep?.progress}%</span>
            </div>
          </div>
        )}

        {processingState === 'complete' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between p-4 bg-success/10 rounded-lg">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-5 w-5 text-success" />
                <div>
                  <p className="font-medium text-success">Processing Complete</p>
                  <p className="text-sm text-muted-foreground">{uploadedFile?.name}</p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={resetUpload}>
                Upload Another
              </Button>
            </div>

            <Tabs defaultValue="transcript" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="transcript" className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  <span className="hidden sm:inline">Transcript</span>
                </TabsTrigger>
                <TabsTrigger value="summary" className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  <span className="hidden sm:inline">Summary</span>
                </TabsTrigger>
                <TabsTrigger value="tasks" className="flex items-center gap-2">
                  <ListTodo className="h-4 w-4" />
                  <span className="hidden sm:inline">Tasks</span>
                </TabsTrigger>
                <TabsTrigger value="moderation" className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="hidden sm:inline">Flags</span>
                </TabsTrigger>
              </TabsList>

              <TabsContent value="transcript" className="mt-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="max-h-64 overflow-y-auto space-y-3 font-mono text-sm">
                      {mockTranscript.trim().split('\n\n').map((line, i) => {
                        const match = line.match(/\[(.+?)\] (.+?): (.+)/);
                        if (match) {
                          return (
                            <div key={i} className="p-2 rounded hover:bg-muted/50">
                              <div className="flex items-center gap-2 mb-1">
                                <Badge variant="outline" className="text-xs">{match[1]}</Badge>
                                <span className="font-semibold text-primary">{match[2]}</span>
                              </div>
                              <p className="text-muted-foreground pl-2">{match[3]}</p>
                            </div>
                          );
                        }
                        return null;
                      })}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="summary" className="mt-4">
                <Card>
                  <CardContent className="pt-4 space-y-4">
                    <div>
                      <h4 className="font-semibold mb-2 flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-secondary" />
                        AI Summary
                      </h4>
                      <p className="text-muted-foreground">{mockSummary.overview}</p>
                    </div>
                    <div>
                      <h4 className="font-semibold mb-2">Key Points</h4>
                      <ul className="space-y-2">
                        {mockSummary.keyPoints.map((point, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                            <CheckCircle2 className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                            {point}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="font-semibold mb-2">Decisions Made</h4>
                      <ul className="space-y-2">
                        {mockSummary.decisions.map((decision, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                            <Badge variant="secondary" className="text-xs">Decision</Badge>
                            {decision}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="tasks" className="mt-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="space-y-3">
                      {mockTasks.map((task) => (
                        <div key={task.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50">
                          <div className="flex items-center gap-3">
                            <Badge 
                              variant="outline" 
                              className={cn(
                                "text-xs",
                                task.priority === 'high' && 'border-destructive text-destructive',
                                task.priority === 'medium' && 'border-warning text-warning',
                                task.priority === 'low' && 'border-muted-foreground'
                              )}
                            >
                              {task.priority}
                            </Badge>
                            <div>
                              <p className="font-medium text-sm">{task.title}</p>
                              <p className="text-xs text-muted-foreground flex items-center gap-2">
                                <Users className="h-3 w-3" />
                                {task.assignee}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Clock className="h-4 w-4" />
                            {task.deadline}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="moderation" className="mt-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="space-y-3">
                      {mockModerationFlags.map((flag, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 border rounded-lg bg-warning/5 border-warning/30">
                          <AlertTriangle className="h-5 w-5 text-warning mt-0.5 flex-shrink-0" />
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="outline" className="text-xs capitalize border-warning text-warning">
                                {flag.type.replace('-', ' ')}
                              </Badge>
                              <span className="text-xs text-muted-foreground">{flag.timestamp}</span>
                            </div>
                            <p className="font-medium text-sm">{flag.speaker}</p>
                            <p className="text-sm text-muted-foreground">{flag.description}</p>
                          </div>
                        </div>
                      ))}
                      {mockModerationFlags.length === 0 && (
                        <div className="text-center py-8 text-muted-foreground">
                          <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-success" />
                          <p>No moderation flags detected</p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default UploadMeeting;
