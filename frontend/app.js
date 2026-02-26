const subjectEl = document.getElementById("subject");
const chaptersEl = document.getElementById("chapters");
const formEl = document.getElementById("paper-form");
const statusEl = document.getElementById("status");
const previewEl = document.getElementById("paper-preview");
const printBtn = document.getElementById("print-btn");

let latestHtml = "";

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json();
}

function selectedMarks() {
  return Array.from(document.querySelectorAll("input[name='marks']:checked"))
    .map((x) => Number(x.value))
    .sort((a, b) => a - b);
}

function selectedChapters() {
  return Array.from(chaptersEl.selectedOptions).map((o) => o.value);
}

async function loadSubjects() {
  const data = await fetchJson("/subjects");
  subjectEl.innerHTML = "";
  for (const subject of data.subjects || []) {
    const opt = document.createElement("option");
    opt.value = subject;
    opt.textContent = subject;
    subjectEl.appendChild(opt);
  }
}

async function loadChapters(subject) {
  const data = await fetchJson(`/chapters/${encodeURIComponent(subject)}`);
  chaptersEl.innerHTML = "";
  for (const chapter of data.chapters || []) {
    const opt = document.createElement("option");
    opt.value = chapter;
    opt.textContent = chapter;
    chaptersEl.appendChild(opt);
  }
}

function setPortionMode() {
  const isChapterMode = document.querySelector("input[name='portion']:checked").value === "chapters";
  chaptersEl.disabled = !isChapterMode;
}

function showPreview(html) {
  previewEl.srcdoc = html;
  latestHtml = html;
  printBtn.disabled = false;
}

async function onSubmit(ev) {
  ev.preventDefault();
  const marks = selectedMarks();
  if (!marks.length) {
    alert("Select at least one marks option.");
    return;
  }

  const isFullPortion = document.querySelector("input[name='portion']:checked").value === "full";
  const payload = {
    subject: subjectEl.value,
    full_portion: isFullPortion,
    chapters: isFullPortion ? [] : selectedChapters(),
    marks_options: marks,
    difficulty: document.getElementById("difficulty").value,
    question_type: document.getElementById("question_type").value,
    additional_instructions: document.getElementById("additional_instructions").value.trim() || null
  };

  if (!payload.full_portion && payload.chapters.length === 0) {
    alert("Select at least one chapter.");
    return;
  }

  statusEl.textContent = "Generating...";
  printBtn.disabled = true;
  try {
    const result = await fetchJson("/generate-paper", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    showPreview(result.html);
    statusEl.textContent = "Generated";
  } catch (err) {
    statusEl.textContent = "Error";
    alert(`Failed to generate paper: ${err.message}`);
  }
}

function printPaper() {
  if (!latestHtml) {
    return;
  }
  const printWin = window.open("", "_blank");
  if (!printWin) {
    alert("Popup blocked. Allow popups and retry.");
    return;
  }
  printWin.document.open();
  printWin.document.write(latestHtml);
  printWin.document.close();
  printWin.focus();
  setTimeout(() => printWin.print(), 300);
}

async function init() {
  try {
    await loadSubjects();
    if (subjectEl.value) {
      await loadChapters(subjectEl.value);
    }
  } catch (err) {
    statusEl.textContent = "Failed to load options";
    alert(`Startup error: ${err.message}`);
  }

  subjectEl.addEventListener("change", async () => {
    await loadChapters(subjectEl.value);
  });
  document.querySelectorAll("input[name='portion']").forEach((el) => {
    el.addEventListener("change", setPortionMode);
  });
  formEl.addEventListener("submit", onSubmit);
  printBtn.addEventListener("click", printPaper);
  setPortionMode();
}

init();
