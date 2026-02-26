import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

type GeneratePayload = {
  subject: string;
  full_portion: boolean;
  chapters: string[];
  marks_options: number[];
  difficulty: string;
  question_type: string;
  additional_instructions: string | null;
};

const MARK_OPTIONS = [1, 2, 3, 5];

export default function App() {
  const appVersion = "v0.2.0";
  const [subjects, setSubjects] = useState<string[]>([]);
  const [chapters, setChapters] = useState<string[]>([]);
  const [subject, setSubject] = useState("");
  const [fullPortion, setFullPortion] = useState(true);
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
  const [marksOptions, setMarksOptions] = useState<number[]>([1, 2, 3, 5]);
  const [difficulty, setDifficulty] = useState("moderate");
  const [questionType, setQuestionType] = useState("board-mix");
  const [extraInstructions, setExtraInstructions] = useState("");
  const [status, setStatus] = useState("Ready");
  const [previewHtml, setPreviewHtml] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [chaptersOpen, setChaptersOpen] = useState(false);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const chapterPanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void loadSubjects();
  }, []);

  useEffect(() => {
    if (subject) {
      void loadChapters(subject);
    }
  }, [subject]);

  async function loadSubjects() {
    const res = await fetch("/subjects");
    const data = await res.json();
    const values = data.subjects ?? [];
    setSubjects(values);
    if (values.length > 0) {
      setSubject(values[0]);
    }
  }

  async function loadChapters(nextSubject: string) {
    const res = await fetch(`/chapters/${encodeURIComponent(nextSubject)}`);
    const data = await res.json();
    setChapters(data.chapters ?? []);
    setSelectedChapters([]);
  }

  function toggleMark(mark: number) {
    setMarksOptions((prev) =>
      prev.includes(mark) ? prev.filter((m) => m !== mark) : [...prev, mark].sort((a, b) => a - b),
    );
  }

  function toggleChapter(chapter: string) {
    setSelectedChapters((prev) =>
      prev.includes(chapter) ? prev.filter((v) => v !== chapter) : [...prev, chapter],
    );
  }

  const canGenerate = useMemo(() => {
    if (!subject || marksOptions.length === 0) return false;
    if (!fullPortion && selectedChapters.length === 0) return false;
    return true;
  }, [fullPortion, marksOptions.length, selectedChapters.length, subject]);

  async function generatePaper() {
    if (!canGenerate) return;

    const payload: GeneratePayload = {
      subject,
      full_portion: fullPortion,
      chapters: fullPortion ? [] : selectedChapters,
      marks_options: marksOptions,
      difficulty,
      question_type: questionType,
      additional_instructions: extraInstructions.trim() || null,
    };

    setStatus("Generating...");
    setIsGenerating(true);
    try {
      const res = await fetch("/generate-paper", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        setStatus("Failed");
        return;
      }
      const data = await res.json();
      setPreviewHtml(data.html ?? "");
      setStatus("Generated");
    } finally {
      setIsGenerating(false);
    }
  }

  function printPdf() {
    if (!previewHtml) return;
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.open();
    win.document.write(previewHtml);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 300);
  }

  function onPreviewLoaded() {
    const frame = iframeRef.current;
    const doc = frame?.contentDocument;
    if (!doc) return;

    let attempts = 0;
    const maxAttempts = 20;

    const capturePages = () => {
      const pages = doc.querySelectorAll(".page");
      const count = pages.length;
      if (count > 1 || attempts >= maxAttempts) {
        setTotalPages(count || 1);
        setCurrentPage(1);
        return;
      }
      attempts += 1;
      window.setTimeout(capturePages, 120);
    };

    capturePages();

    const onScroll = () => {
      const pages = Array.from(doc.querySelectorAll(".page")) as HTMLElement[];
      if (!pages.length) return;
      const viewportTop = doc.documentElement.scrollTop || doc.body.scrollTop || 0;
      let active = 1;
      for (let i = 0; i < pages.length; i += 1) {
        if (pages[i].offsetTop - 30 <= viewportTop) {
          active = i + 1;
        }
      }
      setCurrentPage(active);
    };

    doc.onscroll = onScroll;
  }

  function goToPage(targetPage: number) {
    if (!iframeRef.current?.contentDocument) return;
    const doc = iframeRef.current.contentDocument;
    const pages = doc.querySelectorAll(".page");
    if (targetPage < 1 || targetPage > pages.length) return;
    const target = pages[targetPage - 1] as HTMLElement;
    const top = Math.max(target.offsetTop - 8, 0);
    if (doc.scrollingElement) {
      doc.scrollingElement.scrollTo({ top, behavior: "smooth" });
    } else {
      doc.documentElement.scrollTop = top;
      doc.body.scrollTop = top;
    }
    setCurrentPage(targetPage);
  }

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!chapterPanelRef.current) return;
      if (!chapterPanelRef.current.contains(event.target as Node)) {
        setChaptersOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border bg-card/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1800px] items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <img src="/logo-mark.svg" alt="Examora" className="h-8 w-8 rounded-md" />
            <div>
              <p className="text-sm font-semibold">Examora</p>
              <p className="text-xs text-muted-foreground">Teacher Question Paper Studio</p>
            </div>
          </div>
          <Badge variant="outline">{status}</Badge>
        </div>
      </header>

      <main className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-[430px_1fr]">
        <Card>
          <CardHeader>
            <CardDescription>CBSE X Board Paper Builder</CardDescription>
            <CardTitle className="text-xl">Question Setup</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="subject">Subject</Label>
              <select
                id="subject"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              >
                {subjects.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label>Portion Scope</Label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setFullPortion(true)}
                  className={`rounded-md border px-3 py-1 text-sm ${fullPortion ? "bg-primary text-primary-foreground" : "bg-secondary"}`}
                >
                  Full Portion
                </button>
                <button
                  type="button"
                  onClick={() => setFullPortion(false)}
                  className={`rounded-md border px-3 py-1 text-sm ${!fullPortion ? "bg-primary text-primary-foreground" : "bg-secondary"}`}
                >
                  Selected Chapters
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Chapters</Label>
              <div className="relative" ref={chapterPanelRef}>
                <button
                  type="button"
                  disabled={fullPortion}
                  onClick={() => setChaptersOpen((v) => !v)}
                  className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-50"
                >
                  <span className="truncate text-left">
                    {fullPortion
                      ? "Disabled for Full Portion"
                      : selectedChapters.length > 0
                        ? `${selectedChapters.length} chapters selected`
                        : "Select chapters"}
                  </span>
                  <ChevronDown className="h-4 w-4" />
                </button>
                {!fullPortion && chaptersOpen ? (
                  <div className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-md border border-input bg-card p-2 shadow-lg">
                    {chapters.map((chapter) => (
                      <label key={chapter} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted">
                        <input
                          type="checkbox"
                          checked={selectedChapters.includes(chapter)}
                          onChange={() => toggleChapter(chapter)}
                        />
                        <span>{chapter}</span>
                      </label>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Marks Mix</Label>
              <div className="flex flex-wrap gap-2">
                {MARK_OPTIONS.map((mark) => (
                  <button
                    type="button"
                    key={mark}
                    onClick={() => toggleMark(mark)}
                    className={`rounded-full border px-3 py-1 text-sm ${marksOptions.includes(mark) ? "bg-primary text-primary-foreground" : "bg-secondary"}`}
                  >
                    {mark} Mark
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="difficulty">Difficulty</Label>
                <select
                  id="difficulty"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                >
                  <option value="easy">Easy</option>
                  <option value="moderate">Moderate</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="questionType">Type Bias</Label>
                <select
                  id="questionType"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={questionType}
                  onChange={(e) => setQuestionType(e.target.value)}
                >
                  <option value="board-mix">Board Mix</option>
                  <option value="competency">Competency</option>
                  <option value="case-based">Case Based</option>
                  <option value="pyq-pattern">PYQ Pattern</option>
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="extra">Extra Instructions</Label>
              <Textarea
                id="extra"
                value={extraInstructions}
                onChange={(e) => setExtraInstructions(e.target.value)}
                placeholder="Include assertion-reason and case-based questions."
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={generatePaper} disabled={!canGenerate || isGenerating}>
                Generate Paper
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="min-h-[85vh]">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-lg">Preview</CardTitle>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Badge variant="outline">
                {totalPages > 0 ? `Page ${currentPage} of ${totalPages}` : "No pages"}
              </Badge>
              <Button
                size="sm"
                variant="outline"
                onClick={() => goToPage(currentPage + 1)}
                disabled={totalPages === 0 || currentPage >= totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="h-[calc(100%-84px)] p-0">
            <iframe
              ref={iframeRef}
              onLoad={onPreviewLoaded}
              title="paper-preview"
              srcDoc={previewHtml}
              className="h-[76vh] w-full border-0"
            />
            <div className="flex justify-end border-t border-border p-3">
              <Button variant="secondary" onClick={printPdf} disabled={!previewHtml || isGenerating}>
                Print / Save PDF
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>

      <footer className="border-t border-border bg-card/95 px-4 py-3">
        <div className="mx-auto flex max-w-[1800px] items-center justify-between text-xs text-muted-foreground">
          <p>Copyright © 2026 Examora. All rights reserved.</p>
          <p>{appVersion}</p>
        </div>
      </footer>

      {isGenerating ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-sm">
          <div className="flex items-center gap-3 rounded-lg border bg-card px-5 py-4 shadow-xl">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <div>
              <p className="text-sm font-medium">Generating question paper...</p>
              <p className="text-xs text-muted-foreground">AI is preparing board-style content</p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
