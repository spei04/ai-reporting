const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8001" : "";

const WORK_STEPS = [
  "Receiving uploaded workbook",
  "Inspecting workbook structure",
  "Normalizing support tabs",
  "Resolving source mappings",
  "Generating SCF summary and detailed bridge",
  "Preparing evidence and download artifacts",
];

const SKILL_AGENTS = [
  {
    id: "accounting_memo_draft",
    label: "accounting memo",
    patterns: [/accounting memo/i, /technical memo/i, /position memo/i, /memo draft/i],
  },
  {
    id: "disclosure_checklist",
    label: "disclosure checklist",
    patterns: [/disclosure checklist/i, /correct disclosures/i, /missing disclosures/i, /disclosures? (included|missing|complete)/i],
  },
  {
    id: "disclosure_draft_redline",
    label: "disclosure redline",
    patterns: [/(redline|revise|rewrite|edit).*(disclosure|footnote)/i, /(disclosure|footnote).*(redline|revise|rewrite|edit)/i],
  },
  {
    id: "tie_out_review",
    label: "tie-out review",
    patterns: [/tie[- ]?out/i, /does .* tie/i, /reconcile to/i, /agrees to/i],
  },
  {
    id: "variance_explanation",
    label: "variance explanation",
    patterns: [/variance/i, /flux/i, /fluctuation/i, /quarter over quarter/i, /year over year/i, /\bqoq\b/i, /\byoy\b/i],
  },
  {
    id: "rule_to_claim_coverage",
    label: "rule-to-claim coverage",
    patterns: [/claim.*(support|rule|backed)/i, /(every claim|every sentence)/i, /rule support/i],
  },
  {
    id: "reviewer_findings",
    label: "reviewer findings",
    patterns: [/review findings/i, /review notes/i, /review comments/i, /open items/i, /audit comments/i],
  },
  {
    id: "financial_statement_flux_analysis",
    label: "financial statement flux",
    patterns: [/financial statement flux/i, /balance sheet flux/i, /income statement flux/i, /financial statement movement/i],
  },
  {
    id: "close_package_review",
    label: "close package review",
    patterns: [/close package/i, /close binder/i, /quarter-end close/i, /month-end close/i],
  },
  {
    id: "xbrl_filing_mechanics",
    label: "XBRL filing mechanics",
    patterns: [/xbrl/i, /ixbrl/i, /edgar/i, /filing mechanics/i, /cover page/i, /exhibit/i],
  },
  {
    id: "controls_evidence_review",
    label: "controls evidence",
    patterns: [/sox/i, /control evidence/i, /reviewer signoff/i, /control owner/i],
  },
  {
    id: "contract_accounting",
    label: "contract accounting",
    patterns: [/contract accounting/i, /contract/i, /booking/i, /asc 606/i, /lease contract/i],
  },
  {
    id: "filing_draft",
    label: "filing draft",
    patterns: [/draft.*(filing|disclosure|footnote)/i, /(10-k|10-q|md&a)/i],
  },
  {
    id: "rule_research",
    label: "ASC/SEC rule research",
    patterns: [/\basc\b/i, /\bsec\b/i, /regulation s-[xk]/i, /accounting guidance/i],
  },
  {
    id: "source_trace_evidence",
    label: "source trace",
    patterns: [/source trace/i, /where did/i, /where.*number/i, /evidence/i],
  },
  {
    id: "scf_generation",
    label: "SCF",
    patterns: [/\bscf\b/i, /cash flows?/i, /statement of cash flows/i],
  },
  {
    id: "schedule_generation",
    label: "schedule generation",
    patterns: [/schedule/i, /rollforward/i, /depreciation/i, /lease schedule/i, /debt schedule/i],
  },
  {
    id: "source_file_parsing",
    label: "source file parsing",
    patterns: [/parse/i, /uploaded workbook/i, /support file/i, /template/i],
  },
];

let state = {
  sessionId: null,
  attachments: [],
  artifacts: [],
  objectUrls: [],
  evidenceLinks: [],
  evidencePreview: [],
  library: null,
  librarySection: "uploads",
  ruleFilter: "all",
  messageCounter: 0,
};

document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  await initSession();
  bindComposer();
  bindSuggestions();
  bindDrawer();
  bindSidebar();
  bindSessionUpload();
  renderAttachments();
});

async function initSession() {
  state.sessionId = localStorage.getItem("ai-reporting-session-id");
  if (state.sessionId) {
    document.getElementById("model-status").textContent = "Context ready";
    return;
  }
  try {
    const response = await fetch(apiUrl("/api/sessions"), { method: "POST" });
    const payload = await response.json();
    if (!response.ok || !payload.session_id) throw new Error(payload.message || "Unable to create session");
    state.sessionId = payload.session_id;
    localStorage.setItem("ai-reporting-session-id", state.sessionId);
    document.getElementById("model-status").textContent = "Context ready";
  } catch {
    document.getElementById("model-status").textContent = "Local preview";
  }
}

function bindSidebar() {
  document.addEventListener("click", async (event) => {
    const railButton = event.target.closest?.(".rail-button");
    if (!railButton) return;
    const view = railButton.dataset.view;
    setActiveRail(view);
    if (view === "files") {
      closeUploadPanel(false);
      await openLibrary();
    } else if (view === "upload") {
      closeLibrary(false);
      await openUploadPanel();
    } else {
      closeLibrary(false);
      closeUploadPanel(false);
    }
  });

  document.getElementById("library-close").addEventListener("click", () => closeLibrary(true));
  for (const button of document.querySelectorAll(".library-tab")) {
    button.addEventListener("click", () => {
      state.librarySection = button.dataset.librarySection || "uploads";
      document.querySelectorAll(".library-tab").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      renderLibrary();
    });
  }
}

function setActiveRail(view) {
  document.querySelectorAll(".rail-button").forEach((item) => item.classList.remove("active"));
  const button = document.querySelector(`.rail-button[data-view="${view}"]`);
  if (button) button.classList.add("active");
}

async function openLibrary() {
  await ensureSession();
  document.getElementById("library-panel").classList.add("open");
  await loadLibrary();
}

function closeLibrary(activateChat = true) {
  document.getElementById("library-panel").classList.remove("open");
  if (activateChat) setActiveRail("chat");
}

async function openUploadPanel() {
  await ensureSession();
  document.getElementById("upload-panel").classList.add("open");
  setUploadStatus("Drop files here or choose files to add them to this session.");
}

function closeUploadPanel(activateChat = true) {
  document.getElementById("upload-panel").classList.remove("open");
  if (activateChat) setActiveRail("chat");
}

async function loadLibrary() {
  const content = document.getElementById("library-content");
  content.textContent = "Loading files...";
  try {
    const response = await fetch(apiUrl(`/api/session-library?session_id=${encodeURIComponent(state.sessionId || "")}`));
    const payload = await response.json();
    if (!response.ok || payload.status === "error") throw new Error(payload.message || "Unable to load file library");
    state.library = payload;
    renderLibrary();
  } catch (error) {
    content.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "library-empty";
    empty.textContent = `Unable to load files: ${error.message}`;
    content.appendChild(empty);
  }
}

function renderLibrary() {
  const content = document.getElementById("library-content");
  content.innerHTML = "";
  const library = state.library || { uploads: [], outputs: [], rules: [] };
  if (state.librarySection === "rules") {
    renderRuleLibrary(content, library.rules || []);
    return;
  }
  const items = state.librarySection === "outputs" ? library.outputs || [] : library.uploads || [];
  if (!items.length) {
    content.appendChild(emptyLibraryMessage(state.librarySection === "outputs" ? "Generated files will appear here after this session creates outputs." : "Uploaded files will appear here after you attach files in this session."));
    return;
  }
  items.forEach((item) => content.appendChild(libraryItem(item)));
}

function renderRuleLibrary(content, rules) {
  const filters = document.createElement("div");
  filters.className = "library-filter";
  [
    ["all", "All"],
    ["ASC", "ASC"],
    ["SEC", "SEC"],
  ].forEach(([value, label]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    if (state.ruleFilter === value) button.classList.add("active");
    button.addEventListener("click", () => {
      state.ruleFilter = value;
      renderLibrary();
    });
    filters.appendChild(button);
  });
  content.appendChild(filters);

  const visible = state.ruleFilter === "all" ? rules : rules.filter((item) => item.kind === state.ruleFilter);
  if (!visible.length) {
    content.appendChild(emptyLibraryMessage("No rule documents found."));
    return;
  }
  visible.forEach((item) => content.appendChild(libraryItem(item)));
}

function emptyLibraryMessage(text) {
  const empty = document.createElement("div");
  empty.className = "library-empty";
  empty.textContent = text;
  return empty;
}

function libraryItem(item) {
  const href = item.href ? apiUrl(item.href) : "";
  const link = document.createElement(href ? "a" : "div");
  link.className = "library-item";
  if (href) {
    link.href = href;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.download = "";
  }
  const title = item.name || item.filename || "Untitled file";
  const subtitle = [item.kind, item.filename].filter(Boolean).join(" · ");
  link.innerHTML = `
    <strong>${escapeHtml(title)}</strong>
    <span>${escapeHtml(subtitle || "Downloadable file")}</span>
  `;
  return link;
}

function initTheme() {
  const saved = localStorage.getItem("ai-reporting-theme");
  const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  setTheme(saved || preferred);
  document.getElementById("theme-toggle").addEventListener("click", () => {
    setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  });
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("ai-reporting-theme", theme);
  document.getElementById("theme-toggle").setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} mode`);
}

function bindComposer() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("message-input");
  const fileInput = document.getElementById("file-input");

  input.addEventListener("input", () => autoSizeInput(input));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  fileInput.addEventListener("change", () => {
    state.attachments.push(...Array.from(fileInput.files || []));
    fileInput.value = "";
    renderAttachments();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text && state.attachments.length === 0) return;

    const files = [...state.attachments];
    state.attachments = [];
    input.value = "";
    autoSizeInput(input);
    renderAttachments();
    await sendMessage(text, files);
  });
}

function bindSessionUpload() {
  const input = document.getElementById("session-upload-input");
  const dropzone = document.getElementById("session-dropzone");
  document.getElementById("upload-close").addEventListener("click", () => closeUploadPanel(true));

  input.addEventListener("change", async () => {
    const files = Array.from(input.files || []);
    input.value = "";
    await uploadSessionFiles(files);
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragging");
    });
  });

  dropzone.addEventListener("drop", async (event) => {
    const files = Array.from(event.dataTransfer?.files || []);
    await uploadSessionFiles(files);
  });
}

async function uploadSessionFiles(files) {
  const acceptedFiles = files.filter((file) => /\.(xlsx|csv|docx|pdf|txt)$/i.test(file.name));
  if (!acceptedFiles.length) {
    setUploadStatus("Choose XLSX, CSV, PDF, DOCX, or TXT files.");
    return;
  }

  await ensureSession();
  const formData = new FormData();
  formData.append("session_id", state.sessionId || "");
  acceptedFiles.forEach((file) => formData.append("files", file));
  setUploadStatus(`Uploading ${acceptedFiles.length} file${acceptedFiles.length === 1 ? "" : "s"}...`);

  try {
    const response = await fetch(apiUrl("/api/uploads"), {
      method: "POST",
      headers: state.sessionId ? { "X-Session-ID": state.sessionId } : {},
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok || payload.status === "error") {
      throw new Error(payload.message || "Upload failed");
    }
    if (payload.session_id && payload.session_id !== state.sessionId) {
      state.sessionId = payload.session_id;
      localStorage.setItem("ai-reporting-session-id", state.sessionId);
    }
    state.library = null;
    document.getElementById("model-status").textContent = "Context updated";
    setUploadSuccess(payload.uploaded_files || []);
    if (document.getElementById("library-panel").classList.contains("open")) {
      state.librarySection = "uploads";
      await loadLibrary();
    }
  } catch (error) {
    setUploadStatus(`Upload failed: ${error.message}`);
  }
}

function setUploadStatus(text) {
  const status = document.getElementById("session-upload-status");
  status.textContent = text;
}

function setUploadSuccess(files) {
  const status = document.getElementById("session-upload-status");
  status.innerHTML = "";
  const heading = document.createElement("strong");
  heading.textContent = files.length === 1 ? "Uploaded 1 file" : `Uploaded ${files.length} files`;
  const list = document.createElement("ul");
  files.forEach((file) => {
    const item = document.createElement("li");
    const ingestion = file.ingestion || {};
    const status = ingestion.status ? ` - ${formatIngestionStatus(ingestion)}` : "";
    item.textContent = `${file.filename || "Uploaded file"}${status}`;
    list.appendChild(item);
  });
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "View uploads";
  button.addEventListener("click", async () => {
    closeUploadPanel(false);
    setActiveRail("files");
    state.librarySection = "uploads";
    document.querySelectorAll(".library-tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.librarySection === "uploads");
    });
    await openLibrary();
  });
  status.append(heading, list, button);
}

function formatIngestionStatus(ingestion) {
  if (ingestion.status === "indexed") {
    return `ready${Number.isFinite(ingestion.chunk_count) ? `, ${ingestion.chunk_count} chunks` : ""}`;
  }
  if (ingestion.status === "partial") return "stored, limited searchable text";
  if (ingestion.status === "failed") return ingestion.message || "indexing failed";
  return ingestion.status;
}

function bindSuggestions() {
  for (const button of document.querySelectorAll(".suggestions button")) {
    button.addEventListener("click", async () => {
      const prompt = button.dataset.prompt || button.textContent.trim();
      await sendMessage(prompt, [...state.attachments]);
      state.attachments = [];
      renderAttachments();
    });
  }
}

function bindDrawer() {
  document.getElementById("drawer-close").addEventListener("click", () => {
    document.getElementById("artifact-drawer").classList.remove("open");
  });
}

function autoSizeInput(input) {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
}

function renderAttachments() {
  const list = document.getElementById("attachment-list");
  list.innerHTML = "";
  state.attachments.forEach((file, index) => {
    const chip = document.createElement("span");
    chip.className = "attachment-chip";
    chip.innerHTML = `
      <span title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
      <button type="button" aria-label="Remove ${escapeHtml(file.name)}">x</button>
    `;
    chip.querySelector("button").addEventListener("click", () => {
      state.attachments.splice(index, 1);
      renderAttachments();
    });
    list.appendChild(chip);
  });
}

async function sendMessage(text, files) {
  await ensureSession();
  document.body.classList.add("has-messages");
  appendUserMessage(text, files);
  const assistant = appendAssistantShell();
  const sendButton = document.getElementById("send-button");
  sendButton.disabled = true;

  try {
    if (shouldGenerateScf(text, files)) {
      await handleScfGeneration(text, files, assistant);
    } else {
      await handleMockResponse(text, files, assistant);
    }
  } finally {
    sendButton.disabled = false;
  }
}

async function ensureSession() {
  if (state.sessionId) return state.sessionId;
  await initSession();
  return state.sessionId;
}

function appendUserMessage(text, files) {
  const message = createMessage("user");
  const card = message.querySelector(".message-card");
  card.appendChild(paragraph(text || "Attached files for review."));
  if (files.length) card.appendChild(fileList(files));
  document.getElementById("conversation").appendChild(message);
  scrollConversation();
}

function appendAssistantShell() {
  const message = createMessage("assistant");
  const card = message.querySelector(".message-card");
  card.appendChild(paragraph("I am setting up the reporting workpaper."));
  document.getElementById("conversation").appendChild(message);
  scrollConversation();
  return { message, card };
}

function createMessage(role) {
  const message = document.createElement("article");
  message.className = `message ${role}-message`;
  message.dataset.messageId = String(++state.messageCounter);

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = role === "assistant" ? "AR" : "You";

  const card = document.createElement("div");
  card.className = "message-card";
  message.append(avatar, card);
  return message;
}

function paragraph(text) {
  const p = document.createElement("p");
  p.textContent = text;
  return p;
}

function fileList(files) {
  const list = document.createElement("div");
  list.className = "file-list";
  files.forEach((file) => {
    const pill = document.createElement("span");
    pill.className = "file-pill";
    pill.innerHTML = `<span title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>`;
    list.appendChild(pill);
  });
  return list;
}

function shouldGenerateScf(text, files) {
  const hasWorkbook = files.some((file) => file.name.toLowerCase().endsWith(".xlsx"));
  const asksForCashFlow = /\b(scf|cash flow|statement of cash flows|support tabs?|support workbook)\b/i.test(text);
  return hasWorkbook && asksForCashFlow;
}

function predictedSkillAgent(text, files = []) {
  const prompt = String(text || "");
  for (const agent of SKILL_AGENTS) {
    if (agent.patterns.some((pattern) => pattern.test(prompt))) return agent;
  }
  if (files.length) {
    return { id: "source_file_parsing", label: "source file parsing" };
  }
  return null;
}

function agentFromPayload(payload, fallback = null) {
  const selected = payload?.selected_skill || {};
  if (!selected.id && !selected.name) return fallback;
  const existing = SKILL_AGENTS.find((agent) => agent.id === selected.id);
  return {
    id: selected.id || existing?.id || fallback?.id || "reporting",
    label: existing?.label || agentLabelFromName(selected.name) || fallback?.label || "reporting",
  };
}

function agentLabelFromName(name) {
  return String(name || "")
    .replace(/&/g, "and")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function agentWorkingText(agent) {
  if (!agent) return "Reviewing your reporting task.";
  return `Calling ${agent.label} agent for your task.`;
}

function createAgentStatus(agent) {
  const section = document.createElement("section");
  section.className = "agent-status";
  section.setAttribute("aria-live", "polite");
  section.innerHTML = `
    <div class="walking-robot" aria-hidden="true">
      <span class="robot-antenna"></span>
      <span class="robot-head"><span></span><span></span></span>
      <span class="robot-body"></span>
      <span class="robot-leg left"></span>
      <span class="robot-leg right"></span>
    </div>
    <div>
      <strong>${escapeHtml(agentWorkingText(agent))}</strong>
      <span>Reading the right reporting playbook and session context.</span>
    </div>
  `;
  return section;
}

function updateAgentStatus(status, agent) {
  if (!status || !agent) return;
  const strong = status.querySelector("strong");
  if (strong) strong.textContent = agentWorkingText(agent);
}

async function handleScfGeneration(text, files, assistant) {
  assistant.card.innerHTML = "";
  assistant.card.appendChild(paragraph("I will generate the SCF using the uploaded support workbook and keep the source evidence attached to the output."));

  const progress = createProgressList(WORK_STEPS);
  assistant.card.appendChild(progress.element);
  setStep(progress, 0, "active");
  await sleep(250);
  setStep(progress, 0, "done");
  setStep(progress, 1, "active");
  await sleep(250);

  const workbook = files.find((file) => file.name.toLowerCase().endsWith(".xlsx"));
  const formData = new FormData();
  if (state.sessionId) formData.append("session_id", state.sessionId);
  formData.append("workbook", workbook);

  try {
    setStep(progress, 1, "done");
    setStep(progress, 2, "active");
    await sleep(250);
    setStep(progress, 2, "done");
    setStep(progress, 3, "active");

    const response = await fetch(apiUrl("/api/generate"), {
      method: "POST",
      headers: state.sessionId ? { "X-Session-ID": state.sessionId } : {},
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok || payload.status === "error") {
      throw new Error(payload.message || "SCF generation failed");
    }
    if (payload.session_id && payload.session_id !== state.sessionId) {
      state.sessionId = payload.session_id;
      localStorage.setItem("ai-reporting-session-id", state.sessionId);
    }

    setStep(progress, 3, "done");
    setStep(progress, 4, "active");
    await sleep(250);
    setStep(progress, 4, "done");
    setStep(progress, 5, "active");

    const summary = await buildGenerationSummary(payload, workbook);
    const artifacts = generationArtifacts(payload);
    state.artifacts = artifacts;

    await sleep(200);
    setStep(progress, 5, "done");
    renderSummary(assistant.card, summary);
    if (state.evidencePreview.length) {
      assistant.card.appendChild(renderEvidencePreview(state.evidencePreview));
    }
    assistant.card.appendChild(renderArtifacts(artifacts));
    renderDrawer(artifacts, state.evidencePreview);
    document.getElementById("artifact-drawer").classList.add("open");
    if (document.getElementById("library-panel").classList.contains("open")) {
      await loadLibrary();
    }
  } catch (error) {
    setAllRemainingSteps(progress, "error");
    const notice = document.createElement("div");
    notice.className = "notice";
    notice.textContent = `Generation failed: ${error.message}`;
    assistant.card.appendChild(notice);
  } finally {
    scrollConversation();
  }
}

async function handleMockResponse(text, files, assistant) {
  assistant.card.innerHTML = "";
  const predictedAgent = predictedSkillAgent(text, files);
  const agentStatus = predictedAgent ? createAgentStatus(predictedAgent) : null;
  if (agentStatus) assistant.card.appendChild(agentStatus);
  const progress = createProgressList(["Loading session context", "Retrieving ASC/SEC guidance", "Asking reporting assistant"]);
  assistant.card.appendChild(progress.element);

  try {
    setStep(progress, 0, "active");
    const formData = new FormData();
    if (state.sessionId) formData.append("session_id", state.sessionId);
    formData.append("message", text || "Please review the attached file.");
    files.forEach((file) => formData.append("files", file));
    setStep(progress, 0, "done");
    setStep(progress, 1, "active");

    const response = await fetch(apiUrl("/api/chat"), {
      method: "POST",
      headers: state.sessionId ? { "X-Session-ID": state.sessionId } : {},
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok || payload.status === "error") {
      throw new Error(payload.message || "Chat request failed");
    }
    if (payload.session_id && payload.session_id !== state.sessionId) {
      state.sessionId = payload.session_id;
      localStorage.setItem("ai-reporting-session-id", state.sessionId);
    }

    setStep(progress, 1, "done");
    setStep(progress, 2, "active");
    await sleep(180);
    setStep(progress, 2, "done");
    updateAgentStatus(agentStatus, agentFromPayload(payload, predictedAgent));
    const display = payload.display || { summary: payload.answer || "No response returned." };
    renderStructuredAnswer(assistant.card, display);
    if (Array.isArray(payload.citations) && payload.citations.length) {
      assistant.card.appendChild(renderRuleCitations(payload.citations.slice(0, 3), display));
    }
    if (Array.isArray(payload.artifacts) && payload.artifacts.length) {
      assistant.card.appendChild(renderArtifacts(payload.artifacts));
      renderDrawer(payload.artifacts, []);
      document.getElementById("artifact-drawer").classList.add("open");
      if (document.getElementById("library-panel").classList.contains("open")) {
        await loadLibrary();
      }
    }
    document.getElementById("model-status").textContent = payload.used_live_model ? "GPT connected" : "Local preview";
  } catch (error) {
    setAllRemainingSteps(progress, "error");
    const note = document.createElement("div");
    note.className = "notice";
    note.textContent = `Chat request failed: ${error.message}`;
    assistant.card.appendChild(note);
  }
  scrollConversation();
}

function renderStructuredAnswer(card, display) {
  const answer = document.createElement("section");
  answer.className = "answer-block";

  if (display.support_label) {
    const support = document.createElement("div");
    support.className = `support-state ${display.support_status || ""}`;
    support.innerHTML = `
      <strong>${escapeHtml(cleanDisplayText(display.support_label))}</strong>
      <span>${escapeHtml(cleanDisplayText(display.support_note || ""))}</span>
    `;
    answer.appendChild(support);
  }

  const summary = paragraph(cleanDisplayText(display.summary || "No response returned."));
  summary.className = "answer-summary";
  answer.appendChild(summary);

  if (Array.isArray(display.key_points) && display.key_points.length) {
    const list = document.createElement("ul");
    list.className = "answer-points";
    display.key_points.slice(0, 4).forEach((point) => {
      const li = document.createElement("li");
      li.textContent = cleanDisplayText(point);
      list.appendChild(li);
    });
    answer.appendChild(list);
  }

  if (Array.isArray(display.rule_support) && display.rule_support.length) {
    const tags = document.createElement("div");
    tags.className = "rule-tags";
    display.rule_support.slice(0, 3).forEach((rule) => {
      const tag = document.createElement("span");
      tag.textContent = cleanDisplayText(rule.citation || rule.title || "Rule support");
      tags.appendChild(tag);
    });
    answer.appendChild(tags);
  }

  if (Array.isArray(display.checklist_items) && display.checklist_items.length) {
    answer.appendChild(renderChecklistTable(display.checklist_items));
  }

  if (display.next_step) {
    const next = document.createElement("p");
    next.className = "next-step";
    next.textContent = cleanDisplayText(display.next_step);
    answer.appendChild(next);
  }

  card.appendChild(answer);
}

function renderChecklistTable(items) {
  const section = document.createElement("section");
  section.className = "checklist-table-section";
  const heading = document.createElement("p");
  heading.innerHTML = "<strong>Disclosure checklist</strong>";
  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  const table = document.createElement("table");
  table.className = "evidence-table checklist-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>Status</th>
        <th>Disclosure item</th>
        <th>Rule</th>
        <th>Note</th>
      </tr>
    </thead>
  `;
  const tbody = document.createElement("tbody");
  items.forEach((item) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><span class="check-status">${escapeHtml(cleanDisplayText(item.status || ""))}</span></td>
      <td>${escapeHtml(cleanDisplayText(item.item || ""))}</td>
      <td>${escapeHtml(cleanDisplayText(item.rule || ""))}</td>
      <td>${escapeHtml(cleanDisplayText(item.note || ""))}</td>
    `;
    tbody.appendChild(row);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  section.appendChild(heading);
  section.appendChild(wrap);
  return section;
}

function renderRuleCitations(citations, display = {}) {
  const section = document.createElement("section");
  section.className = "citation-preview";
  const heading = document.createElement("p");
  heading.innerHTML = "<strong>Sources used</strong>";
  const rows = document.createElement("div");
  rows.className = "citation-rows";
  citations.forEach((item, index) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "citation-row";
    const label = item.citation || item.title || "Source";
    const type = item.source_type || item.source || "Source";
    const title = item.title && item.title !== label ? item.title : "";
    const excerpt = item.excerpt || item.text || "";
    row.innerHTML = `
      <div class="citation-topline">
        <span>${escapeHtml(cleanDisplayText(type))}</span>
        <strong>${escapeHtml(cleanDisplayText(label))}</strong>
      </div>
      ${title ? `<span>${escapeHtml(cleanDisplayText(title))}</span>` : ""}
      <em>${escapeHtml(cleanDisplayText(excerpt))}</em>
    `;
    row.addEventListener("click", () => openSourceInspector(citations, index, display));
    rows.appendChild(row);
  });
  section.append(heading, rows);
  return section;
}

function cleanDisplayText(text) {
  return String(text || "")
    .replaceAll("**", "")
    .replaceAll("__", "")
    .replaceAll("`", "")
    .replaceAll("—", " - ")
    .replaceAll("–", " - ")
    .replace(/\b(Yes|No|Sure|Okay|Ok) - /g, "$1, ")
    .replace(/\s+/g, " ")
    .trim();
}

function createProgressList(labels) {
  const element = document.createElement("div");
  element.className = "progress-list";
  const steps = labels.map((label) => {
    const row = document.createElement("div");
    row.className = "progress-step";
    row.innerHTML = `<span class="step-dot" aria-hidden="true"></span><span>${escapeHtml(label)}</span>`;
    element.appendChild(row);
    return row;
  });
  return { element, steps };
}

function setStep(progress, index, stateName) {
  const step = progress.steps[index];
  if (!step) return;
  step.classList.remove("active", "done", "error");
  step.classList.add(stateName);
}

function setAllRemainingSteps(progress, stateName) {
  progress.steps.forEach((step) => {
    if (!step.classList.contains("done")) {
      step.classList.remove("active", "done", "error");
      step.classList.add(stateName);
    }
  });
}

async function buildGenerationSummary(payload, workbook) {
  const evidence = payload.evidence_data || jsonFromInlineArtifact(payload, "evidence_json") || await fetchOptionalJson(payload.evidence_json);
  const mapping = payload.mapping_review_data || jsonFromInlineArtifact(payload, "mapping_review_json") || await fetchOptionalJson(payload.mapping_review_json);
  const issueCount = Array.isArray(mapping)
    ? mapping.filter((item) => item.status === "missing_sheet" || item.status === "needs_review").length
    : null;
  const evidenceCount = Array.isArray(evidence) ? evidence.length : null;
  state.evidenceLinks = normalizeEvidenceLinks(evidence);
  state.evidencePreview = buildEvidencePreview(state.evidenceLinks);

  const items = [
    `Parsed ${workbook.name}.`,
    "Generated the SCF summary and detailed QTD bridge from the support workbook.",
    "Added an Evidence Index sheet and linked generated cells to evidence rows inside the workbook.",
    evidenceCount === null ? "Prepared source evidence links." : `Prepared ${evidenceCount} source evidence links.`,
  ];
  if (issueCount !== null) {
    items.push(issueCount === 0 ? "No blocking mapping exceptions were found." : `${issueCount} mapping items need review.`);
  }
  if (payload.golden_validation) {
    items.push(`Development validation status: ${payload.golden_validation.status}.`);
  }
  return items;
}

function buildEvidencePreview(evidence) {
  if (!Array.isArray(evidence)) return [];
  return evidence
    .map((item, index) => {
      const source = (item.dependency_details || []).find((detail) => detail.source_type === "source_workbook");
      const sourceText = source ? formatSourceLocation(source) : "No direct source workbook cell found";
      return {
        index,
        output: `${item.output_sheet}!${item.output_cell}`,
        value: formatEvidenceValue(item.output_value),
        formula: item.output_formula || "Static/template value",
        source: sourceText,
        rule: item.rule_reference || "Rule support pending",
        status: item.review_status || (source ? "Linked" : "Review"),
      };
    })
    .filter(Boolean)
    .slice(0, 5);
}

function normalizeEvidenceLinks(evidence) {
  if (!Array.isArray(evidence)) return [];
  return evidence.map((item, index) => ({
    ...item,
    evidence_id: item.evidence_id || `${item.output_sheet || "Output"}!${item.output_cell || index}`,
    output_value: item.output_value,
    output_formula: item.output_formula || "",
    dependency_details: Array.isArray(item.dependency_details) ? item.dependency_details : [],
    dependencies: Array.isArray(item.dependencies) ? item.dependencies : [],
    source_locations: Array.isArray(item.source_locations) ? item.source_locations : [],
    review_status: item.review_status || "Review",
  }));
}

function formatSourceLocation(detail) {
  const canonical = detail.key || "";
  const actual = detail.actual_sheet && detail.actual_cell ? `${detail.actual_sheet}!${detail.actual_cell}` : "";
  if (actual && actual !== canonical) return `${canonical} located at ${actual}`;
  return canonical || actual || "Source location pending";
}

function generationArtifacts(payload) {
  const inlineByKey = new Map((payload.inline_artifacts || []).map((item) => [item.key, item]));
  return [
    {
      key: "output_workbook",
      title: "Generated SCF workbook",
      description: "SCF summary, detailed bridge, preserved formulas, and source-linked outputs.",
      href: payload.output_workbook,
      inline: inlineByKey.get("output_workbook"),
      type: "xlsx",
    },
    {
      key: "evidence_json",
      title: "Evidence links",
      description: "Output cells mapped to source cells, formulas, and initial rule support.",
      href: payload.evidence_json,
      inline: inlineByKey.get("evidence_json"),
      type: "json",
    },
    {
      key: "mapping_review_json",
      title: "Mapping review",
      description: "Required support locations, matched uploaded cells, confidence, and review status.",
      href: payload.mapping_review_json,
      inline: inlineByKey.get("mapping_review_json"),
      type: "json",
    },
    {
      key: "normalized_support_json",
      title: "Normalized support",
      description: "Standardized support items parsed from the uploaded workbook.",
      href: payload.normalized_support_json,
      inline: inlineByKey.get("normalized_support_json"),
      type: "json",
    },
  ].filter((artifact) => artifact.href || artifact.inline);
}

function renderSummary(card, items) {
  const heading = document.createElement("p");
  heading.innerHTML = "<strong>SCF generation complete.</strong>";
  const list = document.createElement("ul");
  list.className = "summary-list";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
  card.append(heading, list);
}

function renderArtifacts(artifacts) {
  const wrapper = document.createElement("div");
  const heading = document.createElement("p");
  heading.innerHTML = "<strong>Downloadable outputs</strong>";
  const grid = document.createElement("div");
  grid.className = "artifact-grid";
  artifacts.forEach((artifact) => grid.appendChild(artifactCard(artifact)));
  wrapper.append(heading, grid);
  return wrapper;
}

function renderEvidencePreview(items) {
  const section = document.createElement("section");
  section.className = "evidence-preview";
  const heading = document.createElement("p");
  heading.innerHTML = "<strong>Source trace preview</strong>";
  const rows = document.createElement("div");
  rows.className = "evidence-rows";
  items.forEach((item) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "evidence-row";
    row.innerHTML = `
      <span>${escapeHtml(item.output)} · ${escapeHtml(item.value)} · ${escapeHtml(item.status)}</span>
      <strong>${escapeHtml(item.source)}</strong>
      <em>${escapeHtml(item.rule)}</em>
    `;
    row.addEventListener("click", () => openEvidenceInspector(item.index));
    rows.appendChild(row);
  });
  section.append(heading, rows);
  return section;
}

function artifactCard(artifact) {
  const card = document.createElement("a");
  card.className = "artifact-card";
  card.href = artifactDownloadHref(artifact);
  card.target = "_blank";
  card.rel = "noreferrer";
  card.download = "";
  if (artifact.inline?.filename) card.download = artifact.inline.filename;
  card.innerHTML = `
    <strong>${escapeHtml(artifact.title)}</strong>
    <span>${escapeHtml(artifact.description)}</span>
    <span>${escapeHtml(artifact.type.toUpperCase())}</span>
  `;
  return card;
}

function artifactDownloadHref(artifact) {
  if (artifact.href) return apiUrl(artifact.href);
  if (!artifact.inline?.base64) return "";
  const blob = base64ToBlob(artifact.inline.base64, artifact.inline.mime_type || "application/octet-stream");
  const url = URL.createObjectURL(blob);
  state.objectUrls.push(url);
  return url;
}

function jsonFromInlineArtifact(payload, key) {
  const item = (payload.inline_artifacts || []).find((artifact) => artifact.key === key);
  if (!item?.base64) return null;
  try {
    return JSON.parse(atob(item.base64));
  } catch {
    return null;
  }
}

function base64ToBlob(base64, mimeType) {
  const binary = atob(base64);
  const chunks = [];
  for (let offset = 0; offset < binary.length; offset += 8192) {
    const slice = binary.slice(offset, offset + 8192);
    const bytes = new Uint8Array(slice.length);
    for (let index = 0; index < slice.length; index += 1) {
      bytes[index] = slice.charCodeAt(index);
    }
    chunks.push(bytes);
  }
  return new Blob(chunks, { type: mimeType });
}

function renderDrawer(artifacts, evidencePreview = []) {
  setDrawerHeader("Workspace", "Generated files");
  const body = document.getElementById("drawer-body");
  body.className = "drawer-body";
  body.innerHTML = "";
  if (evidencePreview.length) {
    const note = document.createElement("p");
    note.className = "drawer-note";
    note.textContent = "Click a source trace to inspect the output value, formula, source workbook cells, and rule support.";
    body.appendChild(note);
    body.appendChild(renderEvidencePreview(evidencePreview));
  }
  artifacts.forEach((artifact) => body.appendChild(artifactCard(artifact)));
}

function openEvidenceInspector(selectedIndex = 0) {
  const evidence = state.evidenceLinks[selectedIndex] || state.evidenceLinks[0];
  if (!evidence) return;

  setDrawerHeader("SCF Evidence", `${evidence.output_sheet || "Output"}!${evidence.output_cell || ""}`);
  const body = document.getElementById("drawer-body");
  body.className = "drawer-body source-inspector evidence-inspector";
  body.innerHTML = "";

  const intro = document.createElement("p");
  intro.className = "drawer-note";
  intro.textContent = "Inspect how this generated cash-flow value ties back to the support workbook and rule reference.";
  body.appendChild(intro);

  const outputDetail = document.createElement("section");
  outputDetail.className = "source-detail";
  outputDetail.appendChild(sourceDetailRow("Output sheet", evidence.output_sheet || "Output"));
  outputDetail.appendChild(sourceDetailRow("Output cell", evidence.output_cell || "Cell pending"));
  outputDetail.appendChild(sourceDetailRow("Output value", formatEvidenceValue(evidence.output_value)));
  outputDetail.appendChild(sourceDetailRow("Formula", evidence.output_formula || "Static/template value"));
  outputDetail.appendChild(sourceDetailRow("Rule reference", evidence.rule_reference || "Rule support pending"));
  outputDetail.appendChild(sourceDetailRow("Review status", evidence.review_status || "Review"));
  body.appendChild(outputDetail);

  const dependencies = evidence.dependency_details || [];
  const sourceDependencies = dependencies.filter((detail) => detail.source_type === "source_workbook");
  const generatedDependencies = dependencies.filter((detail) => detail.source_type !== "source_workbook");
  body.appendChild(evidenceDependencyTable("Source workbook cells", sourceDependencies, [
    ["Canonical cell", (detail) => detail.key || ""],
    ["Actual location", (detail) => detail.actual_sheet && detail.actual_cell ? `${detail.actual_sheet}!${detail.actual_cell}` : "Location pending"],
    ["Value", (detail) => formatEvidenceValue(detail.value)],
    ["Formula", (detail) => detail.formula || ""],
  ]));

  if (generatedDependencies.length) {
    body.appendChild(evidenceDependencyTable("Generated dependencies", generatedDependencies, [
      ["Generated cell", (detail) => detail.key || ""],
      ["Value", (detail) => formatEvidenceValue(detail.value)],
      ["Formula", (detail) => detail.formula || "Static/template value"],
    ]));
  }

  if (state.evidencePreview.length > 1) {
    const list = document.createElement("div");
    list.className = "source-list evidence-list";
    const heading = document.createElement("p");
    heading.innerHTML = "<strong>Other traced values</strong>";
    list.appendChild(heading);
    state.evidencePreview.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = item.index === selectedIndex ? "active" : "";
      button.textContent = `${item.output} · ${item.value}`;
      button.addEventListener("click", () => openEvidenceInspector(item.index));
      list.appendChild(button);
    });
    body.appendChild(list);
  }

  document.getElementById("artifact-drawer").classList.add("open");
}

function evidenceDependencyTable(title, rows, columns) {
  const section = document.createElement("section");
  section.className = "evidence-table-section";
  const heading = document.createElement("p");
  heading.innerHTML = `<strong>${escapeHtml(title)}</strong>`;
  section.appendChild(heading);

  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "library-empty";
    empty.textContent = "No rows found for this evidence group.";
    section.appendChild(empty);
    return section;
  }

  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  const table = document.createElement("table");
  table.className = "evidence-table";
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  columns.forEach(([label]) => {
    const th = document.createElement("th");
    th.textContent = label;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach(([, getter]) => {
      const td = document.createElement("td");
      td.textContent = cleanDisplayText(getter(row));
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  section.appendChild(wrap);
  return section;
}

function formatEvidenceValue(value) {
  if (value === null || value === undefined || value === "") return "Blank";
  if (typeof value === "number" && Number.isFinite(value)) {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return cleanDisplayText(value);
}

function openSourceInspector(citations, selectedIndex = 0, display = {}) {
  setDrawerHeader("Sources", "Source details");
  const body = document.getElementById("drawer-body");
  body.className = "drawer-body source-inspector";
  body.innerHTML = "";

  const selected = citations[selectedIndex] || citations[0] || {};
  const intro = document.createElement("p");
  intro.className = "drawer-note";
  intro.textContent = "Inspect the source context used for this answer. These details are for review only and do not create a downloadable output.";
  body.appendChild(intro);

  const detail = document.createElement("section");
  detail.className = "source-detail";
  detail.appendChild(sourceDetailRow("Source type", selected.source_type || selected.source || "Source"));
  detail.appendChild(sourceDetailRow("Citation", selected.citation || selected.title || "Source"));
  if (selected.title && selected.title !== selected.citation) {
    detail.appendChild(sourceDetailRow("Title", selected.title));
  }
  if (selected.location) {
    detail.appendChild(sourceDetailRow("Location", selected.location));
  }
  if (selected.path) {
    detail.appendChild(sourceDetailRow("File", sourceFilename(selected.path)));
  }
  if (selected.score !== undefined && selected.score !== null) {
    detail.appendChild(sourceDetailRow("Retrieval score", String(selected.score)));
  }
  const claim = display.summary || "";
  if (claim) {
    detail.appendChild(sourceDetailRow("Answer context", claim));
  }
  const excerpt = selected.excerpt || selected.text || "";
  detail.appendChild(sourceDetailRow("Retrieved excerpt", excerpt || "No excerpt was available for this source."));
  body.appendChild(detail);

  if (citations.length > 1) {
    const list = document.createElement("div");
    list.className = "source-list";
    const heading = document.createElement("p");
    heading.innerHTML = "<strong>Other sources</strong>";
    list.appendChild(heading);
    citations.forEach((item, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = index === selectedIndex ? "active" : "";
      button.textContent = `${item.number || index + 1}. ${cleanDisplayText(item.citation || item.title || "Source")}`;
      button.addEventListener("click", () => openSourceInspector(citations, index, display));
      list.appendChild(button);
    });
    body.appendChild(list);
  }

  document.getElementById("artifact-drawer").classList.add("open");
}

function sourceDetailRow(label, value) {
  const row = document.createElement("div");
  row.className = "source-detail-row";
  const key = document.createElement("span");
  key.textContent = label;
  const body = document.createElement("p");
  body.textContent = cleanDisplayText(value);
  row.append(key, body);
  return row;
}

function sourceFilename(path) {
  return String(path || "").split(/[\\/]/).filter(Boolean).pop() || "Source file";
}

function setDrawerHeader(kicker, title) {
  document.getElementById("drawer-kicker").textContent = kicker;
  document.getElementById("drawer-title").textContent = title;
}

async function fetchOptionalJson(path) {
  if (!path) return null;
  try {
    const response = await fetch(apiUrl(path));
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

function apiUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path}`;
}

function scrollConversation() {
  requestAnimationFrame(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  });
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
