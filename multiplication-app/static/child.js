/* jshint esversion:11 */
"use strict";

// ── State ────────────────────────────────────────────────────────────────
let currentFact   = null;
let questionStart = null;
let mode          = "keyboard";

// ── DOM refs ─────────────────────────────────────────────────────────────
const screenStart    = document.getElementById("screen-start");
const screenQuestion = document.getElementById("screen-question");
const screenDone     = document.getElementById("screen-done");
const progressFill   = document.getElementById("progress-fill");
const progressLabel  = document.getElementById("progress-label");
const questionCard   = document.getElementById("question-card");
const qA             = document.getElementById("q-a");
const qB             = document.getElementById("q-b");
const modeKeyboard   = document.getElementById("mode-keyboard");
const modeTiles      = document.getElementById("mode-tiles");
const inputAnswer    = document.getElementById("input-answer");
const btnSubmit      = document.getElementById("btn-submit");
const feedback       = document.getElementById("feedback");
const feedbackText   = document.getElementById("feedback-text");
const doneSats       = document.getElementById("done-stats");
const doneEmoji      = document.getElementById("done-emoji");
const confettiWrap   = document.getElementById("confetti-container");

// ── Screens ───────────────────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

// ── Fetch next question ───────────────────────────────────────────────────
async function fetchNext() {
  const res  = await fetch("/child/next");
  const data = await res.json();

  if (data.done) {
    showDone();
    return;
  }

  currentFact   = data;
  mode          = data.mode;
  questionStart = Date.now();

  // Update UI
  qA.textContent = data.a;
  qB.textContent = data.b;

  // Progress
  const pct = data.progress.total > 0
    ? Math.round(data.progress.done / data.progress.total * 100)
    : 0;
  progressFill.style.width = pct + "%";
  progressLabel.textContent = `${data.progress.done} / ${data.progress.total}`;

  // Slide-in animation
  questionCard.classList.remove("slide-in");
  void questionCard.offsetWidth;          // reflow to restart animation
  questionCard.classList.add("slide-in");

  // Show correct mode widgets
  hideFeedback();
  if (mode === "keyboard") {
    modeKeyboard.classList.remove("hidden");
    modeTiles.classList.add("hidden");
    inputAnswer.value = "";
    inputAnswer.focus();
  } else {
    modeKeyboard.classList.add("hidden");
    modeTiles.classList.remove("hidden");
    buildTiles(data.options, data);
  }
}

// ── Tiles ─────────────────────────────────────────────────────────────────
function buildTiles(options, data) {
  const tiles = modeTiles.querySelectorAll(".tile");
  tiles.forEach((btn, i) => {
    btn.textContent = options[i];
    btn.dataset.val = options[i];
    btn.disabled    = false;
    btn.classList.remove("correct-tile", "wrong-tile");
    btn.onclick     = () => submitAnswer(options[i], data.fact_id);
  });
}

// ── Submit answer ─────────────────────────────────────────────────────────
async function submitAnswer(answer, factId) {
  if (currentFact === null) return;

  const responseMs = Date.now() - questionStart;
  currentFact = null;   // prevent double-submit

  // Disable inputs during processing
  inputAnswer.disabled = true;
  modeTiles.querySelectorAll(".tile").forEach(b => (b.disabled = true));

  const res = await fetch("/child/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      fact_id: factId,
      answer: answer,
      response_time_ms: responseMs,
    }),
  });
  const data = await res.json();

  inputAnswer.disabled = false;

  if (data.correct) {
    showCorrectFeedback();
    if (data.streak > 0 && data.streak % 5 === 0) launchConfetti();
  } else {
    showWrongFeedback(data.correct_answer);
  }
}

// ── Feedback ──────────────────────────────────────────────────────────────
function showCorrectFeedback() {
  feedback.className = "feedback correct-fb show";
  feedbackText.textContent = "✓ Świetnie!";
  questionCard.classList.add("pop");
  setTimeout(() => {
    questionCard.classList.remove("pop");
    hideFeedback();
    fetchNext();
  }, 600);
}

function showWrongFeedback(correctAnswer) {
  feedback.className = "feedback wrong-fb show";
  feedbackText.textContent = `✗ To był ${correctAnswer}`;
  questionCard.classList.add("shake");
  setTimeout(() => questionCard.classList.remove("shake"), 300);
  setTimeout(() => {
    hideFeedback();
    fetchNext();
  }, 2000);
}

function hideFeedback() {
  feedback.className = "feedback hidden";
}

// ── Done screen ───────────────────────────────────────────────────────────
async function showDone() {
  const res  = await fetch("/child/session-status");
  const data = await res.json();

  const done    = data.questions_done || 0;
  const correct = data.correct_count  || 0;   // may be 0 if not tracked
  const pct     = done > 0 ? Math.round(correct / done * 100) : 0;

  if (done === 0) {
    doneEmoji.textContent = "😴";
    doneSats.textContent  = "Brak kart do powtórki — wróć jutro lub poproś rodzica o nową grupę.";
  } else {
    doneEmoji.textContent = pct >= 80 ? "🏆" : pct >= 60 ? "👍" : "💪";
    doneSats.textContent  = `${done} pytań · ${pct > 0 ? pct + "% trafnych" : "ukończono"}`;
  }
  showScreen("screen-done");
}

// ── Confetti ──────────────────────────────────────────────────────────────
function launchConfetti() {
  const colors = ["#ff6b6b","#ffd93d","#6bcb77","#4d96ff","#c77dff","#ff9f1c"];
  for (let i = 0; i < 60; i++) {
    const el = document.createElement("div");
    el.className = "confetti-piece";
    el.style.left             = Math.random() * 100 + "vw";
    el.style.background       = colors[Math.floor(Math.random() * colors.length)];
    el.style.animationDelay   = Math.random() * 0.4 + "s";
    el.style.animationDuration = (0.5 + Math.random() * 0.5) + "s";
    el.style.transform        = `rotate(${Math.random()*360}deg)`;
    confettiWrap.appendChild(el);
    el.addEventListener("animationend", () => el.remove());
  }
}

// ── Event listeners ───────────────────────────────────────────────────────
document.getElementById("btn-start").addEventListener("click", async () => {
  await fetch("/child/new-session", { method: "POST" });
  showScreen("screen-question");
  fetchNext();
});

document.getElementById("btn-new-session").addEventListener("click", async () => {
  await fetch("/child/new-session", { method: "POST" });
  showScreen("screen-question");
  fetchNext();
});

btnSubmit.addEventListener("click", () => {
  if (currentFact && inputAnswer.value.trim() !== "") {
    submitAnswer(inputAnswer.value.trim(), currentFact.fact_id);
  }
});

inputAnswer.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && currentFact && inputAnswer.value.trim() !== "") {
    submitAnswer(inputAnswer.value.trim(), currentFact.fact_id);
  }
});
