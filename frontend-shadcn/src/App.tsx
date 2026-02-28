import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, Loader2, Moon, Sun, Trash2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

type TabMode = "question" | "evaluation";
type ThemeMode = "light" | "dark";

type GeneratePayload = {
  subject: string;
  full_portion: boolean;
  chapters: string[];
  marks_options: number[];
  difficulty: string;
  question_type: string;
  additional_instructions: string | null;
  save_paper: boolean;
  paper_name: string | null;
};

type PaperRow = {
  paper_id: string;
  title: string;
  subject: string;
  created_at: string;
};

type EvalRow = {
  evaluation_id: string;
  question_paper_id?: string | null;
  created_at: string;
  total_marks?: number;
  max_marks?: number;
  summary?: string;
  corrected_pdf_url: string;
};

const MARK_OPTIONS = [1, 2, 3, 5];

export default function App() {
  const appVersion = "v0.5.0";
  const [activeTab, setActiveTab] = useState<TabMode>("question");
  const [status, setStatus] = useState("Ready");
  const [isBusy, setIsBusy] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>("light");

  const [subjects, setSubjects] = useState<string[]>([]);
  const [subject, setSubject] = useState("");
  const [chapters, setChapters] = useState<string[]>([]);
  const [fullPortion, setFullPortion] = useState(true);
  const [chaptersOpen, setChaptersOpen] = useState(false);
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
  const [marksOptions, setMarksOptions] = useState<number[]>([1, 2, 3, 5]);
  const [difficulty, setDifficulty] = useState("moderate");
  const [questionType, setQuestionType] = useState("board-mix");
  const [extraInstructions, setExtraInstructions] = useState("");
  const [paperName, setPaperName] = useState("");
  const [previewHtml, setPreviewHtml] = useState("");
  const [papers, setPapers] = useState<PaperRow[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState("");

  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const chapterPanelRef = useRef<HTMLDivElement | null>(null);

  const [answerPdfFile, setAnswerPdfFile] = useState<File | null>(null);
  const [maxTotalMarks, setMaxTotalMarks] = useState(80);
  const [evaluationRows, setEvaluationRows] = useState<EvalRow[]>([]);
  const [correctedPdfUrl, setCorrectedPdfUrl] = useState("");
  const [evaluationSummary, setEvaluationSummary] = useState("");
  const [evaluationScore, setEvaluationScore] = useState("");

  useEffect(() => {
    const stored = window.localStorage.getItem("examora-theme");
    if (stored === "light" || stored === "dark") {
      setTheme(stored);
      return;
    }
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(prefersDark ? "dark" : "light");
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem("examora-theme", theme);
  }, [theme]);

  useEffect(() => {
    void loadSubjects();
    void loadPapers();
    void loadEvaluations();
  }, []);

  useEffect(() => {
    if (subject) {
      void loadChapters(subject);
    }
  }, [subject]);

  useEffect(() => {
    function closeChapterPanel(event: MouseEvent) {
      if (!chapterPanelRef.current) return;
      if (!chapterPanelRef.current.contains(event.target as Node)) {
        setChaptersOpen(false);
      }
    }
    document.addEventListener("mousedown", closeChapterPanel);
    return () => document.removeEventListener("mousedown", closeChapterPanel);
  }, []);

  async function loadSubjects() {
    const res = await fetch("/subjects");
    const data = await res.json();
    const values = data.subjects ?? [];
    setSubjects(values);
    if (!subject && values.length > 0) {
      setSubject(values[0]);
    }
  }

  async function loadChapters(nextSubject: string) {
    const res = await fetch(`/chapters/${encodeURIComponent(nextSubject)}`);
    const data = await res.json();
    setChapters(data.chapters ?? []);
    setSelectedChapters([]);
  }

  async function loadPapers() {
    const res = await fetch("/papers");
    const data = await res.json();
    const rows: PaperRow[] = data.papers ?? [];
    setPapers(rows);
    if (rows.length > 0 && !selectedPaperId) {
      setSelectedPaperId(rows[0].paper_id);
    }
  }

  async function loadEvaluations() {
    const res = await fetch("/evaluation");
    const data = await res.json();
    setEvaluationRows(data.evaluations ?? []);
  }

  function toggleChapter(chapter: string) {
    setSelectedChapters((prev) => (prev.includes(chapter) ? prev.filter((v) => v !== chapter) : [...prev, chapter]));
  }

  function toggleMark(mark: number) {
    setMarksOptions((prev) =>
      prev.includes(mark) ? prev.filter((m) => m !== mark) : [...prev, mark].sort((a, b) => a - b),
    );
  }

  const canGenerate = useMemo(() => {
    if (!subject || marksOptions.length === 0) return false;
    if (!fullPortion && selectedChapters.length === 0) return false;
    return true;
  }, [subject, marksOptions.length, fullPortion, selectedChapters.length]);

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
      save_paper: true,
      paper_name: paperName.trim() || null,
    };

    setStatus("Generating...");
    setIsBusy(true);
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
      if (data.saved_paper?.paper_id) {
        setSelectedPaperId(data.saved_paper.paper_id);
      }
      await loadPapers();
      setStatus("Generated");
    } finally {
      setIsBusy(false);
    }
  }

  async function viewPaperFromList(paperId: string) {
    const res = await fetch(`/papers/${paperId}`);
    if (!res.ok) return;
    const data = await res.json();
    setPreviewHtml(data.paper?.html ?? "");
    setSelectedPaperId(paperId);
    setActiveTab("question");
    setStatus("Loaded");
  }

  async function deletePaper(paperId: string) {
    const ok = window.confirm("Delete this stored question paper?");
    if (!ok) return;
    await fetch(`/papers/${paperId}`, { method: "DELETE" });
    await loadPapers();
    if (selectedPaperId === paperId) {
      setSelectedPaperId("");
      setPreviewHtml("");
    }
  }

  function onPreviewLoaded() {
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    let attempts = 0;
    const capture = () => {
      const pages = doc.querySelectorAll(".page");
      if (pages.length > 0 || attempts > 20) {
        setTotalPages(pages.length || 1);
        setCurrentPage(1);
        return;
      }
      attempts += 1;
      window.setTimeout(capture, 120);
    };
    capture();
  }

  function goToPage(target: number) {
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    const pages = doc.querySelectorAll(".page");
    if (target < 1 || target > pages.length) return;
    const anchor = pages[target - 1] as HTMLElement;
    const top = Math.max(anchor.offsetTop - 8, 0);
    doc.scrollingElement?.scrollTo({ top, behavior: "smooth" });
    setCurrentPage(target);
  }

  function printQuestionPaper() {
    if (!previewHtml) return;
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.open();
    win.document.write(previewHtml);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 300);
  }

  async function evaluateAnswerSheet() {
    if (!answerPdfFile || !selectedPaperId) return;
    const formData = new FormData();
    formData.append("answer_pdf", answerPdfFile);
    formData.append("question_paper_id", selectedPaperId);
    formData.append("max_total_marks", String(maxTotalMarks));

    setStatus("Evaluating...");
    setIsBusy(true);
    try {
      const res = await fetch("/evaluation/evaluate-answer-sheet", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        setStatus("Failed");
        return;
      }
      const data = await res.json();
      setCorrectedPdfUrl(data.corrected_pdf_url ?? "");
      setEvaluationSummary(data.summary ?? "");
      setEvaluationScore(`${data.total_marks ?? 0}/${data.max_marks ?? maxTotalMarks}`);
      await loadEvaluations();
      setStatus("Evaluation Done");
    } finally {
      setIsBusy(false);
    }
  }

  async function openEvaluation(evaluationId: string) {
    const res = await fetch(`/evaluation/${evaluationId}`);
    if (!res.ok) return;
    const data = await res.json();
    setCorrectedPdfUrl(`/evaluation/${evaluationId}/corrected-pdf`);
    const ev = data.evaluation ?? {};
    setEvaluationSummary(ev.summary ?? "");
    setEvaluationScore(`${ev.total_marks ?? 0}/${ev.max_marks ?? "-"}`);
    setActiveTab("evaluation");
  }

  async function deleteEvaluationRow(evaluationId: string) {
    const ok = window.confirm("Delete this corrected answer record?");
    if (!ok) return;
    await fetch(`/evaluation/${evaluationId}`, { method: "DELETE" });
    await loadEvaluations();
    if (correctedPdfUrl.includes(evaluationId)) {
      setCorrectedPdfUrl("");
      setEvaluationSummary("");
      setEvaluationScore("");
    }
  }

  function printCorrectedPdf() {
    if (!correctedPdfUrl) return;
    const win = window.open(correctedPdfUrl, "_blank");
    if (!win) return;
    setTimeout(() => win.print(), 500);
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border bg-card/95 backdrop-blur">
        <div className="mx-auto flex min-h-14 max-w-[1800px] items-center justify-between gap-3 px-4 py-2">
          <div className="flex items-center gap-2">
            <img src="/logo-mark.svg" alt="Examora" className="h-8 w-8 rounded-md" />
            <div>
              <p className="text-sm font-semibold">Examora</p>
              <p className="text-xs text-muted-foreground">Question Preparation & Answer Correction</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
              className="gap-2"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              {theme === "dark" ? "Light" : "Dark"}
            </Button>
            <Badge variant="outline">{status}</Badge>
          </div>
        </div>
      </header>

      <main className="space-y-4 p-4">
        <div className="flex gap-2">
          <Button variant={activeTab === "question" ? "default" : "secondary"} onClick={() => setActiveTab("question")}>
            Question Preparation
          </Button>
          <Button variant={activeTab === "evaluation" ? "default" : "secondary"} onClick={() => setActiveTab("evaluation")}>
            Answer Correction
          </Button>
        </div>

        {activeTab === "question" ? (
          <section className="grid grid-cols-1 gap-4 lg:grid-cols-[430px_1fr]">
            <Card>
              <CardHeader>
                <CardDescription>Create and store question papers</CardDescription>
                <CardTitle className="text-xl">Question Setup</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Paper Name (optional)</Label>
                  <input
                    value={paperName}
                    onChange={(e) => setPaperName(e.target.value)}
                    className="w-full rounded-md border border-input p-2 text-sm"
                    placeholder="Science Model Paper - Unit Test 1"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Subject</Label>
                  <select
                    className="w-full rounded-md border border-input p-2 text-sm"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                  >
                    {subjects.map((row) => (
                      <option key={row} value={row}>
                        {row}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Portion Scope</Label>
                  <div className="flex gap-2">
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
                        key={mark}
                        type="button"
                        onClick={() => toggleMark(mark)}
                        className={`rounded-full border px-3 py-1 text-sm ${marksOptions.includes(mark) ? "bg-primary text-primary-foreground" : "bg-secondary"}`}
                      >
                        {mark} Mark
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Difficulty</Label>
                    <select
                      className="w-full rounded-md border border-input p-2 text-sm"
                      value={difficulty}
                      onChange={(e) => setDifficulty(e.target.value)}
                    >
                      <option value="easy">Easy</option>
                      <option value="moderate">Moderate</option>
                      <option value="hard">Hard</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label>Type Bias</Label>
                    <select
                      className="w-full rounded-md border border-input p-2 text-sm"
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
                  <Label>Additional Instructions</Label>
                  <Textarea
                    value={extraInstructions}
                    onChange={(e) => setExtraInstructions(e.target.value)}
                    placeholder="Add specific style or constraints."
                  />
                </div>
                <Button onClick={generatePaper} disabled={!canGenerate || isBusy}>
                  Generate & Save Paper
                </Button>
              </CardContent>
            </Card>

            <Card className="min-h-[85vh]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-lg">Question Paper Preview</CardTitle>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1}>
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Badge variant="outline">{totalPages ? `Page ${currentPage} of ${totalPages}` : "No pages"}</Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => goToPage(currentPage + 1)}
                    disabled={!totalPages || currentPage >= totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="max-h-36 overflow-auto rounded-md border border-border">
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 bg-muted">
                      <tr>
                        <th className="px-2 py-1">Stored Papers</th>
                        <th className="px-2 py-1">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {papers.map((p) => (
                        <tr key={p.paper_id} className="border-t">
                          <td className="px-2 py-1">
                            <button className="text-left text-primary hover:underline" onClick={() => viewPaperFromList(p.paper_id)}>
                              {p.title} ({p.subject})
                            </button>
                          </td>
                          <td className="px-2 py-1">
                            <button onClick={() => deletePaper(p.paper_id)} className="inline-flex items-center gap-1 text-red-600 hover:underline">
                              <Trash2 className="h-3.5 w-3.5" />
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <iframe
                  ref={iframeRef}
                  onLoad={onPreviewLoaded}
                  title="paper-preview"
                  srcDoc={previewHtml}
                  className="h-[58vh] w-full rounded-md border border-border"
                />
                <div className="flex justify-end">
                  <Button variant="secondary" onClick={printQuestionPaper} disabled={!previewHtml}>
                    Print / Save PDF
                  </Button>
                </div>
              </CardContent>
            </Card>
          </section>
        ) : (
          <section className="grid grid-cols-1 gap-4 lg:grid-cols-[430px_1fr]">
            <Card>
              <CardHeader>
                <CardDescription>Select stored question paper and upload answer PDF</CardDescription>
                <CardTitle className="text-xl">Answer Correction</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Question Paper</Label>
                  <select
                    className="w-full rounded-md border border-input p-2 text-sm"
                    value={selectedPaperId}
                    onChange={(e) => setSelectedPaperId(e.target.value)}
                  >
                    <option value="">Select saved paper</option>
                    {papers.map((p) => (
                      <option key={p.paper_id} value={p.paper_id}>
                        {p.title} ({p.subject})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Student Answer Sheet PDF</Label>
                  <input
                    type="file"
                    accept="application/pdf"
                    onChange={(e) => setAnswerPdfFile(e.target.files?.[0] ?? null)}
                    className="w-full rounded-md border border-input p-2 text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Maximum Marks</Label>
                  <input
                    type="number"
                    min={1}
                    max={200}
                    value={maxTotalMarks}
                    onChange={(e) => setMaxTotalMarks(Number(e.target.value || 80))}
                    className="w-full rounded-md border border-input p-2 text-sm"
                  />
                </div>
                <Button onClick={evaluateAnswerSheet} disabled={!selectedPaperId || !answerPdfFile || isBusy}>
                  Evaluate & Save Correction
                </Button>
              </CardContent>
            </Card>

            <Card className="min-h-[85vh]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-lg">Corrected Answers</CardTitle>
                <Badge variant="outline">{evaluationScore || "No score"}</Badge>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="max-h-36 overflow-auto rounded-md border border-border">
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 bg-muted">
                      <tr>
                        <th className="px-2 py-1">Corrections</th>
                        <th className="px-2 py-1">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evaluationRows.map((row) => (
                        <tr key={row.evaluation_id} className="border-t">
                          <td className="px-2 py-1">
                            <button className="text-left text-primary hover:underline" onClick={() => openEvaluation(row.evaluation_id)}>
                              {row.evaluation_id} ({row.total_marks ?? 0}/{row.max_marks ?? 0})
                            </button>
                          </td>
                          <td className="px-2 py-1">
                            <button
                              onClick={() => deleteEvaluationRow(row.evaluation_id)}
                              className="inline-flex items-center gap-1 text-red-600 hover:underline"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {evaluationSummary ? <div className="rounded-md border border-border bg-muted p-3 text-sm">{evaluationSummary}</div> : null}
                <iframe title="corrected-pdf-preview" src={correctedPdfUrl} className="h-[56vh] w-full rounded-md border border-border" />
                {correctedPdfUrl ? (
                  <div className="text-sm text-muted-foreground">
                    If preview does not load,{" "}
                    <a href={correctedPdfUrl} target="_blank" rel="noreferrer" className="text-primary underline">
                      open corrected PDF in new tab
                    </a>
                    .
                  </div>
                ) : null}
                <div className="flex justify-end">
                  <Button variant="secondary" onClick={printCorrectedPdf} disabled={!correctedPdfUrl}>
                    Print Corrected PDF
                  </Button>
                </div>
              </CardContent>
            </Card>
          </section>
        )}
      </main>

      <footer className="border-t border-border bg-card/95 px-4 py-3">
        <div className="mx-auto flex max-w-[1800px] items-center justify-between text-xs text-muted-foreground">
          <p>Copyright © 2026 Examora. All rights reserved.</p>
          <p>{appVersion}</p>
        </div>
      </footer>

      {isBusy ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-sm">
          <div className="flex items-center gap-3 rounded-lg border bg-card px-5 py-4 shadow-xl">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <div>
              <p className="text-sm font-medium">Processing request...</p>
              <p className="text-xs text-muted-foreground">Please wait</p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
