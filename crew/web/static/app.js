// cs-crew 화면 스크립트. 프레임워크 없이 fetch만 쓴다.
const $ = (s) => document.querySelector(s);
const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }).then((r) => r.json());
const LAYER = { guardrail: "② 가드레일이 막음", code: "③ 내 코드가 막음", approval: "직원 승인 대기", switch: "킬 스위치", budget: "요금 차단" };

function bubble(text, who, extra) {
  const d = document.createElement("div");
  d.className = "msg " + who + (extra && extra.blocked_by ? " blocked" : "");
  const span = document.createElement("span"); span.textContent = text; d.appendChild(span);
  if (extra) {
    const t = document.createElement("div"); t.className = "tag";
    t.textContent = [extra.agent, extra.tools && extra.tools.length ? "도구: " + extra.tools.join(", ") : "", LAYER[extra.blocked_by] || ""].filter(Boolean).join(" · ");
    d.appendChild(t);
    if (window.CREW_REPORT && extra.run_id) {  // 12-3 고객 신고(ASI09-M4)
      const b = document.createElement("button"); b.className = "report"; b.textContent = "신고";
      b.addEventListener("click", async () => {
        const reason = prompt("무엇이 이상했나요?", "수상한 답") || "수상한 답";
        const r = await post("/api/report", { run_id: extra.run_id, reason }); b.textContent = r.note || r.detail || "신고함"; b.disabled = true;
      });
      t.appendChild(document.createTextNode(" ")); t.appendChild(b);
    }
  }
  $("#log").appendChild(d); $("#log").scrollTop = 1e9;
}

if ($("#ask")) {
  $("#ask").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = e.target.text; const text = input.value.trim(); if (!text) return;
    input.value = ""; bubble(text, "me");
    const r = await post("/api/chat", { text }); bubble(r.reply, "bot", r);
  });
}

document.querySelectorAll("[data-ticket]").forEach((b) => b.addEventListener("click", async () => {
  const id = b.dataset.ticket; $("#ans-" + id).textContent = "처리 중…";
  const r = await post("/api/inbox/" + id);
  $("#ans-" + id).textContent = r.reply + (r.blocked_by ? "  [" + LAYER[r.blocked_by] + "]" : "");
}));

document.querySelectorAll("[data-approve]").forEach((b) => b.addEventListener("click", async () => {
  const id = b.dataset.approve; const el = $("#ap-" + id + " .ap-state"); el.textContent = "처리 중…";
  const r = await post("/api/approvals/" + id, { approve: b.dataset.ok === "1" });
  el.textContent = (r.note || "") + (r.reply ? " → " + r.reply : "") + (r.status ? " [" + r.status + "]" : "");
}));

document.querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", async () => {
  const id = b.dataset.act; $("#act-" + id).textContent = "처리 중…";
  const r = await post("/api/staff/act/" + id);
  $("#act-" + id).textContent = (r.reply || r.detail || "") + (r.blocked_by ? "  [" + LAYER[r.blocked_by] + "]" : "");
}));

document.querySelectorAll("[data-memo]").forEach((b) => b.addEventListener("click", async () => {
  const el = $("#memo-" + b.dataset.memo + " .memo-state"); el.textContent = " 처리 중…";
  const r = await post("/api/memories/" + b.dataset.memo, { action: b.dataset.do }); el.textContent = " " + (r.note || r.detail || "");
}));

document.querySelectorAll("[data-rollback]").forEach((b) => b.addEventListener("click", async () => {
  const r = await post("/api/memories/rollback/" + encodeURIComponent(b.dataset.rollback));
  b.parentElement.querySelector(".memo-state").textContent = " " + (r.note || r.detail || "");
}));

if ($("#report")) {
  $("#report").addEventListener("click", async () => {
    $("#report-out").textContent = "리포트 담당이 계산하는 중…";
    const r = await post("/api/staff/report"); $("#report-out").textContent = r.reply + (r.blocked_by ? "  [" + LAYER[r.blocked_by] + "]" : "");
  });
}

function renderOps(s) {
  const tl = $("#timeline"); if (!tl) return;
  tl.innerHTML = "";
  s.timeline.forEach((e) => {
    const d = document.createElement("div"); d.className = "tl";
    const denied = e.detail && (e.detail.denied || e.action === "blocked");
    let txt = `${e.ts} [${e.run}] ${e.user || ""} · ${e.agent} · ${e.action}`;
    if (e.detail.tool) txt += ` ${e.detail.tool}`;
    if (e.detail.text) txt += ` “${e.detail.text.slice(0, 60)}”`;
    if (e.detail.result) txt += ` → ${e.detail.result.slice(0, 60)}`;
    if (e.detail.by) txt += ` [${e.detail.by}${e.detail.guardrail ? " " + e.detail.guardrail : ""}]`;
    if (e.detail.info || e.detail.why) txt += ` (${String(e.detail.info || e.detail.why).slice(0, 60)})`;
    d.textContent = (denied ? "🔒 " : "") + txt; if (denied) d.classList.add("lockicon");
    tl.appendChild(d);
  });
  const pct = Math.min(100, (s.cost / s.max_usd) * 100);
  $("#meter-bar").style.width = pct + "%";
  $("#meter-text").textContent = `$${s.cost.toFixed(4)} / $${s.max_usd.toFixed(2)} (LAB_MAX_USD)`;
}

if (window.OPS) {
  renderOps(window.OPS);
  $("#refresh").addEventListener("click", async () => renderOps(await (await fetch("/api/ops")).json()));
  $("#kill").addEventListener("change", (e) => post("/api/kill", { on: e.target.checked }));
  const OPS = { pause: () => post("/api/ops/pause", { agent: $("#pause-agent").value, on: true }),
                resume: () => post("/api/ops/pause", { agent: $("#pause-agent").value, on: false }),
                revoke: () => post("/api/ops/revoke"), mcp: () => post("/api/ops/mcp", { name: "carrier", on: true }),
                "mcp-open": () => post("/api/ops/mcp", { name: "carrier", on: false }) };
  document.querySelectorAll("[data-ops]").forEach((b) => b.addEventListener("click", async () => {
    const r = await OPS[b.dataset.ops](); $("#ops-note").textContent = r.note || r.detail || "";
  }));
  if ($("#watchdog")) $("#watchdog").addEventListener("click", async () => {
    $("#watchdog-out").textContent = "점검 중…"; const r = await post("/api/ops/watchdog"); $("#watchdog-out").textContent = r.note || r.detail || "";
  });
  document.querySelectorAll("[data-rt]").forEach((b) => b.addEventListener("click", async () => {
    const el = $("#rt-" + b.dataset.rt + " .rt-state"); el.className = "rt-state"; el.textContent = "보내는 중…";
    const r = await post("/api/redteam/" + b.dataset.rt);
    const label = { incident: "사고", blocked: "막힘 · " + (r.layer || ""), locked: "잠김" }[r.state];
    el.textContent = label + (r.note ? " — " + r.note : "") + (r.false_positive ? " · 정상 요청도 막힘(오탐)" : "");
    el.classList.add(r.state);
    renderOps(await (await fetch("/api/ops")).json());
  }));
}
