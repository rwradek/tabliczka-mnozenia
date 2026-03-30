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
  const res = await fetch("/parent/stats");
  statsData  = await res.json();

  renderGrid(statsData.grid);
  renderBoxes(statsData.box_cards, statsData.phase_info);
  renderHistory(statsData.completed_sessions, statsData.difficult_facts);
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
      cell.classList.add(`box-${Math.max(box, 0)}`);
      cell.innerHTML = `<span class="cell-fact">${a}×${b}</span>
                        <span class="cell-box">${box > 0 ? "B" + box : "—"}</span>`;
      cell.title = `${a}×${b}=${a * b}  [Box ${box}]`;
      wrap.appendChild(cell);
    }
  }
}

// ── TAB 2: Boxes ──────────────────────────────────────────────────────────
const BOX_COLORS = {
  0: "#bdc3c7", 1: "#e74c3c", 2: "#e67e22",
  3: "#f1c40f", 4: "#2ecc71", 5: "#27ae60"
};

function renderBoxes(boxCards, phaseInfo) {
  const wrap  = document.getElementById("boxes-wrap");
  const label = document.getElementById("phase-info-label");
  wrap.innerHTML = "";

  if (phaseInfo) {
    if (phaseInfo.phase === "groups") {
      const grp = phaseInfo.current_group || "—";
      label.textContent =
        `Faza 1 – nauka grup | Aktualna grupa: ${grp} | `+
        `Czyste sesje: ${phaseInfo.consecutive_clean}/2 | `+
        `Postęp: ${phaseInfo.progress}`;
    } else {
      label.textContent =
        `Faza 2 – Leitner | Aktualny box: ${phaseInfo.current_box} | `+
        `Czyste serie: ${phaseInfo.consecutive_clean}/2`;
    }
  }

  for (let i = 1; i <= 5; i++) {
    const cards = (boxCards && boxCards[String(i)]) || [];
    const section = document.createElement("div");
    section.className = "box-section";

    const header = document.createElement("div");
    header.className = "box-section-header";
    header.innerHTML =
      `<span class="box-title" style="color:${BOX_COLORS[i]}">Box ${i}</span>` +
      `<span class="box-meta">${cards.length} kart</span>`;
    section.appendChild(header);

    if (cards.length === 0) {
      const empty = document.createElement("div");
      empty.className = "box-empty";
      empty.textContent = "brak kart";
      section.appendChild(empty);
    } else {
      const list = document.createElement("div");
      list.className = "box-card-list";
      for (const c of cards) {
        const chip = document.createElement("span");
        chip.className = "fact-chip";
        chip.textContent = `${c.a}×${c.b}`;
        chip.title = `${c.a}×${c.b}=${c.result}`;
        list.appendChild(chip);
      }
      section.appendChild(list);
    }
    wrap.appendChild(section);
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

  const PAD  = { top: 20, bottom: 30, left: 36, right: 16 };
  const cW   = W - PAD.left - PAD.right;
  const cH   = H - PAD.top  - PAD.bottom;
  const step = cW / (last14.length - 1);

  ctx.strokeStyle = "#e0e6f0";
  ctx.lineWidth   = 1;
  for (const pct of [0, 25, 50, 75, 100]) {
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

  const points = last14.map((s, i) => [
    PAD.left + i * step,
    PAD.top + cH - ((s.accuracy || 0) / 100) * cH,
  ]);

  ctx.beginPath();
  ctx.moveTo(...points[0]);
  for (let i = 1; i < points.length; i++) {
    const [px, py] = points[i - 1];
    const [cx, cy] = points[i];
    ctx.bezierCurveTo(px + step / 2, py, cx - step / 2, cy, cx, cy);
  }
  ctx.strokeStyle = "#5b8dee";
  ctx.lineWidth   = 2.5;
  ctx.stroke();

  ctx.lineTo(points[points.length - 1][0], PAD.top + cH);
  ctx.lineTo(points[0][0], PAD.top + cH);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + cH);
  grad.addColorStop(0, "rgba(91,141,238,.25)");
  grad.addColorStop(1, "rgba(91,141,238,0)");
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.fillStyle = "#5b8dee";
  for (const [x, y] of points) {
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.fillStyle  = "#7f8c8d";
  ctx.font       = "10px sans-serif";
  ctx.textAlign  = "center";
  last14.forEach((s, i) => {
    if (i % 2 !== 0) return;
    const x    = PAD.left + i * step;
    const date = (s.completed_at || "").substring(5, 10);
    ctx.fillText(date, x, H - PAD.bottom + 14);
  });
}

// ── TAB 4: Settings ───────────────────────────────────────────────────────
async function loadSettings() {
  const res  = await fetch("/parent/settings");
  const data = await res.json();
  const form = document.getElementById("settings-form");
  const modeRadio = form.querySelector(`[name="answer_mode"][value="${data.answer_mode}"]`);
  if (modeRadio) modeRadio.checked = true;
}

document.getElementById("settings-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  await fetch("/parent/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer_mode: fd.get("answer_mode") }),
  });
  alert("Zapisano ustawienia.");
});

// ── Init ──────────────────────────────────────────────────────────────────
loadStats();
loadSettings();
