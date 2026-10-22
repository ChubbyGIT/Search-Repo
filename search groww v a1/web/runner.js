const $ = id => document.getElementById(id);
const BASE = location.origin;
const NAMES = { angelone: "Angel One", groww: "Groww", groww_ind: "Groww Individual" };
const BROKER_COLOR = { angelone: "blue", groww: "green", groww_ind: "violet" };
const BROKER_LOGO = {
  angelone: "https://www.google.com/s2/favicons?domain=angelone.in&sz=64",
  groww: "https://www.google.com/s2/favicons?domain=groww.in&sz=64",
  groww_ind: "https://www.google.com/s2/favicons?domain=groww.in&sz=64",
};
const TYPE_TAG = { CE: "tag-green", PE: "tag-red", FUT: "tag-violet" };
const TOP_N = 10;
const IDX_COL_PX = 34;
const MIN_SHARE = 0.15;
const COL_SHARES_KEY = "colShares";
const blockState = {};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ---------- theme ---------- */
const SUN = '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';
const MOON = '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>';
function applyTheme(t) {
  if (t === "light") document.documentElement.setAttribute("data-theme", "light");
  else document.documentElement.removeAttribute("data-theme");
  $("theme-icon").innerHTML = t === "light" ? SUN : MOON;
}
applyTheme(localStorage.getItem("theme") === "light" ? "light" : "dark");
$("theme-toggle").onclick = () => {
  const t = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
  localStorage.setItem("theme", t); applyTheme(t);
};

/* ---------- topbar height ---------- */
function syncTopbar() {
  document.documentElement.style.setProperty("--topbar-h", document.querySelector(".topbar").offsetHeight + "px");
}
syncTopbar(); window.addEventListener("resize", syncTopbar);

/* ---------- broker selection ---------- */
let broker = localStorage.getItem("broker") || "all";
let growwInd = localStorage.getItem("growwInd") === "1";
function applyBrokers() {
  document.querySelectorAll("#chips .chip").forEach(c => c.classList.toggle("active", c.dataset.b === broker));
  $("chip-groww-ind").classList.toggle("active", growwInd);
  const sel = selectedBrokers();
  for (const b of Object.keys(NAMES)) $("info-" + b).classList.toggle("hidden", !sel.includes(b));
}
function setBroker(b) { broker = b; localStorage.setItem("broker", b); applyBrokers(); }
function selectedBrokers() {
  const base = broker === "all" ? ["angelone", "groww"] : [broker];
  return growwInd ? [...base, "groww_ind"] : base;
}
$("chips").addEventListener("click", e => { const c = e.target.closest(".chip"); if (c) setBroker(c.dataset.b); });
$("chip-groww-ind").onclick = () => { growwInd = !growwInd; localStorage.setItem("growwInd", growwInd ? "1" : "0"); applyBrokers(); };
localStorage.removeItem("kws");
applyBrokers();

/* ---------- health ---------- */
async function health() {
  try { const r = await fetch(BASE + "/api/health"); if (!r.ok) throw 0; $("backend").className = "status ok"; $("backend-text").textContent = "backend online"; }
  catch { $("backend").className = "status down"; $("backend-text").textContent = "backend offline"; }
}
health(); setInterval(health, 10000);

/* ---------- console ---------- */
$("console-toggle").onclick = () => $("console").classList.toggle("collapsed");
function log(msg, cls) {
  const el = $("log"), t = new Date().toLocaleTimeString();
  const line = document.createElement("div");
  if (cls) line.style.color = cls === "err" ? "var(--red)" : "var(--green)";
  line.textContent = `[${t}] ${msg}`;
  el.appendChild(line); el.scrollTop = el.scrollHeight;
}

/* ---------- token validation ---------- */
const TOKEN_FIELDS = { angelone: ["ntt-token", "ntt-error"], groww_ind: ["groww-token", "groww-error"] };
function validateTokens(brokers) {
  let ok = true;
  for (const [b, [inp, err]] of Object.entries(TOKEN_FIELDS)) {
    if (!brokers.includes(b)) continue;
    if (!$(inp).value.trim()) { $(inp).classList.add("input-error"); $(err).classList.add("show"); ok = false; }
  }
  return ok;
}
for (const [inp, err] of Object.values(TOKEN_FIELDS))
  $(inp).addEventListener("input", () => { $(inp).classList.remove("input-error"); $(err).classList.remove("show"); });

/* ---------- column shares / resizers ---------- */
function loadColShares(n) {
  try {
    const s = (JSON.parse(localStorage.getItem(COL_SHARES_KEY)) || {})[n];
    if (Array.isArray(s) && s.length === n) return s;
  } catch {}
  return Array(n).fill(1 / n);
}
function saveColShares(n, shares) {
  let all = {}; try { all = JSON.parse(localStorage.getItem(COL_SHARES_KEY)) || {}; } catch {}
  all[n] = shares; localStorage.setItem(COL_SHARES_KEY, JSON.stringify(all));
}
function colgroupHtml(brokers) {
  const sh = loadColShares(brokers.length);
  let h = `<colgroup><col class="c-idx" style="width:${IDX_COL_PX}px">`;
  sh.forEach(s => { h += `<col style="width:${(s * 62).toFixed(3)}%"><col style="width:${(s * 38).toFixed(3)}%">`; });
  return h + "</colgroup>";
}
function applyShares(container, shares) {
  const cols = container.querySelectorAll("col:not(.c-idx)");
  shares.forEach((s, i) => { cols[i * 2].style.width = (s * 62) + "%"; cols[i * 2 + 1].style.width = (s * 38) + "%"; });
}
function placeResizer(el, container, shares, i) {
  const w = container.querySelector("table").offsetWidth - IDX_COL_PX;
  const cum = shares.slice(0, i + 1).reduce((a, b) => a + b, 0);
  el.style.left = (IDX_COL_PX + cum * w) + "px";
}
function wireColumnResizers(container, brokers) {
  container.querySelectorAll(".col-resizer").forEach(e => e.remove());
  const n = brokers.length; if (n < 2) return;
  let shares = loadColShares(n);
  for (let i = 0; i < n - 1; i++) {
    const el = document.createElement("div"); el.className = "col-resizer";
    container.appendChild(el); placeResizer(el, container, shares, i);
    el.addEventListener("mousedown", ev => {
      ev.preventDefault(); el.classList.add("dragging");
      const startX = ev.clientX, start = shares.slice();
      const w = container.querySelector("table").offsetWidth - IDX_COL_PX;
      const move = m => {
        const d = (m.clientX - startX) / w, pair = start[i] + start[i + 1];
        const a = Math.min(pair - MIN_SHARE, Math.max(MIN_SHARE, start[i] + d));
        shares = start.slice(); shares[i] = a; shares[i + 1] = pair - a;
        applyShares(container, shares);
        container.querySelectorAll(".col-resizer").forEach((r, k) => placeResizer(r, container, shares, k));
      };
      const up = () => {
        el.classList.remove("dragging");
        document.removeEventListener("mousemove", move); document.removeEventListener("mouseup", up);
        saveColShares(n, shares);
      };
      document.addEventListener("mousemove", move); document.addEventListener("mouseup", up);
    });
  }
}

/* ---------- table rendering ---------- */
function exchTagColor(label) {
  const l = (label || "").toUpperCase();
  return l.startsWith("NSE") ? "tag-blue" : l.startsWith("BSE") ? "tag-amber" : l.startsWith("MCX") ? "tag-grey" : l.startsWith("CDS") ? "tag-violet" : "tag-grey";
}
function instrumentCell(r) {
  if (!r) return '<td class="muted"></td>';
  const ex = r.exch_label || r.exchange;
  let h = `<span class="sym">${esc(r.symbol)}</span>`;
  if (ex) h += `<span class="tag inst-tag ${exchTagColor(ex)}">${esc(ex)}</span>`;
  if (r.option_type) h += `<span class="tag inst-tag ${TYPE_TAG[r.option_type] || "tag-grey"}">${esc(r.option_type)}</span>`;
  if (r.expiry) h += `<span class="sym-sub">${esc(r.expiry)}</span>`;
  return `<td title="${esc(r.symbol)}">${h}</td>`;
}
function underlyingCell(r, last) {
  return `<td class="muted${last ? " col-divider" : ""}">${r ? esc(r.underlying) : ""}</td>`;
}
function combinedTable(id, brokers, data, expanded) {
  const span = brokers.length * 2 + 1;
  if (!data) return `<div class="scroll"><table>${colgroupHtml(brokers)}<tbody><tr><td colspan="${span}"><span class="loader"></span>Searching…</td></tr></tbody></table></div>`;
  let banner = '<th class="idxcol"></th>', labels = '<th class="idxcol">#</th>';
  for (const b of brokers) {
    const d = data[b] || {}, c = BROKER_COLOR[b];
    const cnt = d.source === "error" ? `<span class="broker-count err">${esc(d.error)}</span>`
      : `<span class="broker-count">${(d.rows || []).length} results${d.source === "captured" ? " · captured " + esc(d.captured_at) : ""}</span>`;
    banner += `<th colspan="2" class="broker-head broker-${c} col-divider"><div class="broker-head-row"><img alt="" src="${BROKER_LOGO[b]}"><span>${NAMES[b]}</span>${cnt}</div></th>`;
    labels += `<th class="broker-sub broker-${c}">Instrument</th><th class="broker-sub broker-${c} col-divider">Underlying</th>`;
  }
  const lists = brokers.map(b => (data[b] && data[b].rows) || []);
  const max = Math.max(0, ...lists.map(l => l.length));
  const shown = expanded ? max : Math.min(max, TOP_N);
  let body = "";
  if (!max) body = `<tr><td colspan="${span}" class="muted">No results</td></tr>`;
  for (let i = 0; i < shown; i++) {
    body += `<tr><td class="idx">${i + 1}</td>`;
    lists.forEach(l => { body += instrumentCell(l[i]) + underlyingCell(l[i], true); });
    body += "</tr>";
  }
  if (max > TOP_N) body += `<tr><td colspan="${span}" class="expand-row"><button class="expand-btn" data-id="${id}">${expanded ? "Show top " + TOP_N : "Show all (" + max + ")"}</button></td></tr>`;
  return `<div class="scroll"><table>${colgroupHtml(brokers)}<thead><tr>${banner}</tr><tr>${labels}</tr></thead><tbody>${body}</tbody></table></div>`;
}
function paintBlock(id, kw, when) {
  const st = blockState[id], el = $(id);
  el.innerHTML = `<div class="kw-head"><h2>Results for <span class="q">${esc(kw)}</span></h2><span class="muted mono">${esc(when || "")}</span></div>` +
    combinedTable(id, st.brokers, st.data, st.expanded);
  el.querySelectorAll(".expand-btn").forEach(b => b.onclick = () => { st.expanded = !st.expanded; paintBlock(id, kw, when); });
  wireColumnResizers(el.querySelector(".scroll"), st.brokers);
}
function renderBlock(kw, brokers, data) {
  const id = "kw-" + kw.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  let el = $(id);
  if (!el) { el = document.createElement("div"); el.id = id; el.className = "kw-block"; }
  if (!el.isConnected) $("results").appendChild(el);
  blockState[id] = { brokers, data, expanded: false };
  paintBlock(id, kw, data ? new Date().toLocaleTimeString() : "");
}

/* ---------- run ---------- */
async function run() {
  const brokers = selectedBrokers();
  const kws = $("kws").value.split(/[,\n]/).map(s => s.trim()).filter(Boolean);
  if (!kws.length) return;
  if (!validateTokens(brokers)) { log("missing token — add it above and run again", "err"); return; }
  $("go").disabled = true; $("results").innerHTML = "";
  for (const k of Object.keys(blockState)) delete blockState[k];
  for (const kw of kws) {
    renderBlock(kw, brokers, null);
    try {
      const p = new URLSearchParams({
        keyword: kw, brokers: brokers.join(","),
        ntt_token: $("ntt-token").value.trim(), groww_token: $("groww-token").value.trim(),
      });
      const r = await fetch(`${BASE}/api/search?${p}`);
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      log(`"${kw}": ` + brokers.map(b => `${NAMES[b]} ${(data[b].rows || []).length} (${data[b].source})`).join(" · "));
      renderBlock(kw, brokers, data);
    } catch (e) {
      log(`"${kw}": ${e.message}`, "err");
      renderBlock(kw, brokers, Object.fromEntries(brokers.map(b => [b, { source: "error", error: e.message, rows: [] }])));
    }
    await sleep(400);
  }
  log("done", "ok"); $("go").disabled = false;
}
$("search-form").addEventListener("submit", e => { e.preventDefault(); run(); });
$("go").onclick = run;
$("clear").onclick = () => { $("results").innerHTML = ""; $("kws").value = ""; };
document.addEventListener("keydown", e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); $("kws").focus(); } });
