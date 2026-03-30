/* jshint esversion:11 */
"use strict";

// ── Tab switching ─────────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("tab-" + tab.dataset.tab).classList.add("active");
  });
});

// ── Fetch & render all stats ──────────────────────────────────────────────
let statsData = null;

async function loadStats() {
  const res  = await fetch("/parent/stats");
  statsData  = await res.json();

  renderGrid(statsData.grid);
  renderBoxes(statsData.box_counts, statsData.box_next);
  renderHistory(statsData.completed_sessions, statsData.difficult_facts);
  renderSuggestion(statsData.suggested_group, statsData.groups);
}

// ── TAB 1: Grid ───────────────────────────────────────────────────────────
function renderGrid(grid) {
  const wrap = document.getElementById("grid-wrap");
  wrap.innerHTML = "";

  // Column headers (×2 … ×9)
  const corner = document.createElement("div");
  corner.className = "grid-header";
  corner.textContent = "";
  wrap.appendChild(corner);

  for (let b = 2; b <= 9; b++) {
    const h = document.createElement("div");
    h.className = "grid-header";
    h.textContent = "×" + b;
    wrap.appendChild(h);
  }

  // Rows (a = 2 … 9)
  for (let a = 2; a <= 9; a++) {
    // Row header
    const rh = document.createElement("div");
    rh.className = "grid-header";
    rh.textContent = a + "×";
    wrap.appendChild(rh);

    for (let b = 2; b <= 9; b++) {
      const fid  = `${a}x${b}`;
      const info = grid[fid];
      const cell = document.createElement("div");
      const box  = info ? info.box : 0;

      cell.className = "grid-cell";
      if (!info || !info.active) {
        cell.classList.add("box-0");
      } else {
        cell.classList.add(`box-${Math.max(box, 0)}`);
      }

      cell.innerHTML = `<span class="cell-fact">${a}×${b}</span>
                        <span class="cell-box">${box > 0 ? "B" + box : "—"}</span>`;
      cell.title = `${a}×${b}=${a * b}  [Box ${box}]`;
      wrap.appendChild(cell);
    }
  }
}

// ── TAB 2: Boxes ──────────────────────────────────────────────────────────
const BOX_INTERVALS = { 1: "1 dzień", 2: "2 dni", 3: "4 dni", 4: "8 dni", 5: "16 dni" };
const BOX_COLORS    = { 0: "#bdc3c7", 1: "#e74c3c", 2: "#e67e22", 3: "#f1c40f", 4: "#2ecc71", 5: "#27ae60" };

function renderBoxes(counts, nextDates) {
  const wrap    = document.getElementById("boxes-wrap");
  const totalActive = [1,2,3,4,5].reduce((s, i) => s + (counts[String(i)] || 0), 0);
  wrap.innerHTML = "";

  for (let i = 1; i <= 5; i++) {
    const cnt  = counts[String(i)] || 0;
    const pct  = totalActive > 0 ? Math.round(cnt / totalActive * 100) : 0;
    const next = nextDates[String(i)];

    const card = document.createElement("div");
    card.className = "box-card";
    card.style.borderTop = `4px solid ${BOX_COLORS[i]}`;
    card.innerHTML = `
      <div class="box-num" style="color:${BOX_COLORS[i]}">Box ${i}</div>
      <div class="box-count">${cnt} kart</div>
      <div class="box-interval">Powtórka co: ${BOX_INTERVALS[i]}</div>
      ${next ? `<div class="box-interval">Następna: ${next}</div>` : ""}
      <div class="box-bar"><div class="box-bar-fill" style="width:${pct}%;background:${BOX_COLORS[i]}"></div></div>
    `;
    wrap.appendChild(card);
  }
}

// ── TAB 3: History ────────────────────────────────────────────────────────
function renderHistory(sessions, difficult) {
  renderChart(sessions);

  const tbody = document.getElementById("sessions-body");
  tbody.innerHTML = "";
  const reversed = [...sessions].reverse();
  for (const s of reversed) {
    const dt  = s.completed_at ? s.completed_at.replace("T", " ").substring(0, 16) : "—";
    const avg = s.avg_response_ms ? (s.avg_response_ms / 1000).toFixed(1) + "s" : "—";
    const tr  = document.createElement("tr");
    tr.innerHTML = `
      <td>${dt}</td>
      <td>${s.answers || 0}</td>
      <td>${s.accuracy != null ? s.accuracy + "%" : "—"}</td>
      <td>${avg}</td>
    `;
    tbody.appendChild(tr);
  }

  const ul = document.getElementById("difficult-list");
  ul.innerHTML = "";
  if (!difficult || difficult.length === 0) {
    ul.innerHTML = "<li>Brak danych o błędach.</li>";
    return;
  }
  for (const d of difficult) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span><strong>${d.a} × ${d.b} = ${d.result}</strong></span>
      <span class="error-badge">${d.errors} błędów z ${d.total}</span>
    `;
    ul.appendChild(li);
  }
}

function renderChart(sessions) {
  const canvas = document.getElementById("accuracy-chart");
  const ctx    = canvas.getContext("2d");
  const W      = canvas.width;
  const H      = canvas.height;

  ctx.clearRect(0, 0, W, H);

  // Background
  ctx.fillStyle = "#fff";
  ctx.roundRect(0, 0, W, H, 14);
  ctx.fill();

  const last14 = sessions.slice(-14);
  if (last14.length < 2) {
    ctx.fillStyle = "#7f8c8d";
    ctx.font = "14px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Za mało danych do wykresu.", W / 2, H / 2);
    return;
  }

  const PAD = { top: 20, bottom: 30, left: 36, right: 16 };
  const cW   = W - PAD.left - PAD.right;
  const cH   = H - PAD.top  - PAD.bottom;
  const step = cW / (last14.length - 1);

  // Grid lines
  ctx.strokeStyle = "#e0e6f0";
  ctx.lineWidth   = 1;
  for (let pct of [0, 25, 50, 75, 100]) {
    const y = PAD.top + cH - (pct / 100) * cH;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(W - PAD.right, y);
    ctx.stroke();

    ctx.fillStyle  = "#7f8c8d";
    ctx.font       = "11px sans-serif";
    ctx.textAlign  = "right";
    ctx.fillText(pct + "%", PAD.left - 4, y + 4);
  }

  // Line
  const points = last14.map((s, i) => [
    PAD.left + i * step,
    PAD.top + cH - ((s.accuracy || 0) / 100) * cH,
  ]);

  ctx.beginPath();
  ctx.moveTo(...points[0]);
  for (let i = 1; i < points.length; i++) {
    const [px, py] = points[i - 1];
    const [cx, cy] = points[i];
    ctx.bezierCurveTo(
      px + step / 2, py,
      cx - step / 2, cy,
      cx, cy
    );
  }
  ctx.strokeStyle = "#5b8dee";
  ctx.lineWidth   = 2.5;
  ctx.stroke();

  // Fill under line
  ctx.lineTo(points[points.length - 1][0], PAD.top + cH);
  ctx.lineTo(points[0][0], PAD.top + cH);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + cH);
  grad.addColorStop(0, "rgba(91,141,238,.25)");
  grad.addColorStop(1, "rgba(91,141,238,0)");
  ctx.fillStyle = grad;
  ctx.fill();

  // Dots
  ctx.fillStyle = "#5b8dee";
  for (const [x, y] of points) {
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  // X-axis labels (every other, abbreviated date)
  ctx.fillStyle  = "#7f8c8d";
  ctx.font       = "10px sans-serif";
  ctx.textAlign  = "center";
  last14.forEach((s, i) => {
    if (i % 2 !== 0) return;
    const x    = PAD.left + i * step;
    const date = (s.completed_at || "").substring(5, 10); // MM-DD
    ctx.fillText(date, x, H - PAD.bottom + 14);
  });
}

// ── TAB 4: Settings ───────────────────────────────────────────────────────
async function loadSettings() {
  const res  = await fetch("/parent/settings");
  const data = await res.json();

  const form = document.getElementById("settings-form");
  form.querySelector(`[name="session_length_min"]`).value    = data.session_length_min;
  form.querySelector(`[name="session_hard_limit_min"]`).value = data.session_hard_limit_min;
  form.querySelector(`[name="new_cards_per_session"]`).value = data.new_cards_per_session;
  form.querySelector(`[name="autosave_every_n"]`).value      = data.autosave_every_n;
  form.querySelector(`[name="mastery_threshold_ms"]`).value  = data.mastery_threshold_ms;

  const modeRadio = form.querySelector(`[name="answer_mode"][value="${data.answer_mode}"]`);
  if (modeRadio) modeRadio.checked = true;
}

document.getElementById("settings-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const fd   = new FormData(form);

  const body = {
    answer_mode:           fd.get("answer_mode"),
    session_length_min:    Number(fd.get("session_length_min")),
    session_hard_limit_min: Number(fd.get("session_hard_limit_min")),
    new_cards_per_session: Number(fd.get("new_cards_per_session")),
    autosave_every_n:      Number(fd.get("autosave_every_n")),
    mastery_threshold_ms:  Number(fd.get("mastery_threshold_ms")),
  };

  await fetch("/parent/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  alert("Zapisano ustawienia.");
});

// ── Suggestion ────────────────────────────────────────────────────────────
let suggestedGroupId = null;

function renderSuggestion(suggestion, groups) {
  const textEl = document.getElementById("suggestion-text");
  const select = document.getElementById("group-override");

  // Populate override dropdown with pending groups
  select.innerHTML = '<option value="">— zmień grupę —</option>';
  for (const [gid, info] of Object.entries(groups)) {
    if (info.status === "pending") {
      const opt = document.createElement("option");
      opt.value       = gid;
      opt.textContent = gid;
      select.appendChild(opt);
    }
  }

  if (suggestion) {
    suggestedGroupId = suggestion.group;
    const reasonMap = {
      ready:      "Wszystkie aktywne grupy osiągnęły Box 3",
      regression: "Niektóre karty cofnęły się do Box 1",
      stagnation: "Brak postępu przez 5+ dni",
    };
    textEl.textContent =
      `Następna proponowana grupa: ${suggestion.group} — ${reasonMap[suggestion.reason] || suggestion.reason}`;
  } else {
    suggestedGroupId = null;
    textEl.textContent = "Brak sugestii – kontynuuj aktywne grupy.";
  }
}

document.getElementById("btn-approve").addEventListener("click", async () => {
  if (!suggestedGroupId) return;
  await fetch("/parent/override-group", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ group_id: suggestedGroupId }),
  });
  loadStats();
});

document.getElementById("btn-override").addEventListener("click", async () => {
  const sel = document.getElementById("group-override");
  if (!sel.value) return;
  await fetch("/parent/override-group", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ group_id: sel.value }),
  });
  loadStats();
});

// ── Init ──────────────────────────────────────────────────────────────────
loadStats();
loadSettings();
