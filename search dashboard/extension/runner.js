// Angel One vs Groww search compare.
// Groww: opens groww.in in a background tab (a normal visit in your own browser), reads the
//        rendered results, stores them via the local backend.
// Angel One: the local backend calls Angel One's official SmartAPI search.
const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const BASE = "http://127.0.0.1:8000";
const GROWW_URL = "https://groww.in/search?q={q}";   // fixed, not user-editable
const NAMES = { angelone: "Angel One", groww: "Groww" };
const TAGS = { angelone: ["AO", "tag-blue"], groww: ["GW", "tag-green"] };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

$("groww-url").textContent = GROWW_URL;

// ---------- console ----------
let logStarted = false;
function log(msg, cls = "") {
  if (!logStarted) { $("log").innerHTML = ""; logStarted = true; }
  const ts = new Date().toLocaleTimeString("en-GB");
  $("log").insertAdjacentHTML("beforeend", `<span class="ts">${ts}</span>  <span class="${cls}">${esc(msg)}</span>\n`);
  $("log").scrollTop = 1e9;
}

// ---------- broker chips + persistence ----------
let broker = "all";
function setBroker(b) {
  broker = b;
  document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c.dataset.b === b));
  const sel = selectedBrokers();
  ["angelone", "groww"].forEach((x) => $("info-" + x).classList.toggle("hidden", !sel.includes(x)));
  chrome.storage.local.set({ broker: b });
}
function selectedBrokers() { return broker === "all" ? ["angelone", "groww"] : [broker]; }
document.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => setBroker(c.dataset.b)));

chrome.storage.local.get(["kws", "broker"], (d) => {
  if (d.kws) $("kws").value = d.kws.replace(/\n+/g, ", ");
  setBroker(["all", "angelone", "groww"].includes(d.broker) ? d.broker : "all");
});
$("kws").addEventListener("input", () => chrome.storage.local.set({ kws: $("kws").value }));

// ---------- backend status ----------
async function checkBackend() {
  const el = $("backend");
  try {
    await fetch(BASE + "/");
    el.className = "status ok"; el.querySelector(".status-text").textContent = "backend online";
  } catch {
    el.className = "status down"; el.querySelector(".status-text").textContent = "backend offline";
  }
}
checkBackend(); setInterval(checkBackend, 10000);

// ---------- tab helpers (retry: Chrome rejects tab edits while a tab is being dragged) ----------
async function retry(fn, tries = 10) {
  for (let i = 0; ; i++) {
    try { return await fn(); } catch (e) {
      if (i >= tries || !/cannot be edited|dragging/i.test(e.message || "")) throw e;
      await sleep(400);
    }
  }
}
function waitForLoad(tabId, timeout = 20000) {
  return new Promise((resolve) => {
    const done = () => { chrome.tabs.onUpdated.removeListener(l); clearTimeout(t); resolve(); };
    const l = (id, info) => { if (id === tabId && info.status === "complete") done(); };
    const t = setTimeout(done, timeout);
    chrome.tabs.onUpdated.addListener(l);
    chrome.tabs.get(tabId, (tab) => { if (tab && tab.status === "complete") done(); });
  });
}

// ---------- injected into the Groww page ----------
function growwPageScript() {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const lines = (el) => el.innerText.split("\n").map((s) => s.trim()).filter(Boolean);
  const read = () => {
    // Scope to the block right after the "SEARCH RESULTS" heading so the unrelated
    // "trending" widget is never picked up.
    const h = [...document.querySelectorAll("*")].find(
      (e) => e.children.length === 0 && /^search results$/i.test(e.textContent.trim()));
    if (!h) return [];
    const scope = h.nextElementSibling || (h.parentElement && h.parentElement.nextElementSibling);
    if (!scope) return [];
    return [...scope.querySelectorAll('[class*="SearchPageV2_suggestionItem"]')].map((el) => {
      const t = lines(el); return { symbol: t[0], underlying: t[1] || null };
    });
  };
  return (async () => {
    let last = -1, stable = 0, rows = [];
    for (let i = 0; i < 40; i++) {
      await wait(300);
      rows = read();
      if (rows.length && rows.length === last) { if (++stable >= 3) break; } else stable = 0;
      last = rows.length;
    }
    return { rows, note: rows.length ? "" : "no results found on the page" };
  })();
}

async function captureGroww(kw) {
  const url = GROWW_URL.replace("{q}", encodeURIComponent(kw));
  const tab = await retry(() => chrome.tabs.create({ url, active: false }));
  try {
    await waitForLoad(tab.id);
    const [res] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: growwPageScript });
    const { rows: raw, note } = res.result || { rows: [], note: "script returned nothing" };
    if (!raw.length) { log(`groww  "${kw}"  0 rows, not saved (${note})`, "warn"); return; }
    const rows = raw.map((r) => ({
      symbol: r.symbol, full_name: r.underlying, underlying: r.underlying, exchange: null,
      segment: null, expiry: null, strike: null, option_type: null, price: null, change_pct: null }));
    const resp = await fetch(BASE + "/api/snapshot", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ broker: "groww", keyword: kw, rows }) });
    log(`groww  "${kw}"  ${rows.length} rows captured  [${resp.status}]`, resp.ok ? "ok" : "err");
  } finally {
    await retry(() => chrome.tabs.remove(tab.id)).catch(() => {});
  }
}

// ---------- rendering ----------
function badges(d) {
  switch (d.source) {
    case "live": return `<span class="tag tag-blue">LIVE API</span>`;
    case "mixed": return `<span class="tag tag-blue">LIVE API</span><span class="tag tag-amber">+ TEXT MATCH</span>`;
    case "local": return `<span class="tag tag-amber">TEXT MATCH</span>`;
    case "captured": return `<span class="tag tag-green">CAPTURED</span>`;
    case "error": return `<span class="tag tag-red">ERROR</span>`;
    default: return `<span class="tag tag-amber">FALLBACK</span>`;
  }
}
function note(d) {
  switch (d.source) {
    case "mixed": return `Angel One's API only matches the start of a symbol — rows tagged TXT come from Angel One's instrument list. Order is relevance-ranked by this tool.`;
    case "local": return `Angel One's API returned nothing — rows are substring matches from Angel One's instrument list.`;
    case "captured": return `Captured from groww.in · ${esc(d.captured_at)}`;
    case "error": return esc(d.error);
    case "fallback": return `Not captured — plain text match on the instrument list, not Groww's real search.`;
    default: return "";
  }
}
const TYPE_TAG = { CE: "tag-green", PE: "tag-red", FUT: "tag-violet", EQ: "tag-blue" };
function fmtNum(v) { return v == null ? "" : Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

function row(r, i) {
  const c = r.change_pct;
  const dir = c > 0 ? "up" : c < 0 ? "down" : "";
  const arrow = c > 0 ? " ▲" : c < 0 ? " ▼" : "";
  const tags = [
    r.option_type ? `<span class="tag ${TYPE_TAG[r.option_type] || "tag-grey"}">${esc(r.option_type)}</span>` : "",
    r.exchange ? `<span class="tag tag-grey">${esc(r.exchange)}</span>` : "",
    r.match === "text" ? `<span class="tag tag-amber">TXT</span>` : "",
  ].join("");
  return `<tr>
    <td class="idx">${i + 1}</td>
    <td><div class="inst"><span class="sym">${esc(r.symbol)}</span>${r.expiry ? `<span class="sym-sub">${esc(r.expiry)}</span>` : ""}${tags}</div></td>
    <td class="muted">${esc(r.underlying)}</td>
    <td class="r num">${r.strike != null ? fmtNum(r.strike) : ""}</td>
    <td class="r num ${dir}">${r.price != null ? "₹" + fmtNum(r.price) + arrow : ""}</td>
    <td class="r num ${dir}">${c != null ? (c > 0 ? "+" : "") + c.toFixed(2) + "%" : ""}</td>
  </tr>`;
}
function card(b, d) {
  const [t, cls] = TAGS[b];
  let body;
  if (!d) body = `<div class="empty"><span class="loader"></span> fetching</div>`;
  else if (!d.rows.length) body = `<div class="empty">No results</div>`;
  else body = `<div class="scroll"><table><thead><tr>
      <th>#</th><th>Instrument</th><th>Underlying</th><th class="r">Strike</th><th class="r">LTP</th><th class="r">Change</th>
    </tr></thead><tbody>${d.rows.map(row).join("")}</tbody></table></div>`;
  const n = d ? note(d) : "";
  return `<section class="card">
    <div class="card-h"><span class="tag ${cls}">${t}</span><h3>${NAMES[b]}</h3>
      <div class="badges">${d ? `<span class="muted">${d.rows.length} results</span>` + badges(d) : ""}</div></div>
    ${n ? `<div class="card-note">${n}</div>` : ""}
    ${body}</section>`;
}
function renderBlock(kw, brokers, data) {
  const id = "kw-" + kw.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  let el = document.getElementById(id);
  if (!el) {
    el = document.createElement("div");
    el.id = id; el.className = "kw-block";
    $("results").prepend(el);
  }
  const when = new Date().toLocaleTimeString("en-GB");
  el.innerHTML = `<div class="kw-head"><h2>Results for <span class="q">"${esc(kw)}"</span></h2><span class="meta">${when}</span></div>
    <div class="grid" style="--cols:${brokers.length}">${brokers.map((b) => card(b, data && data[b])).join("")}</div>`;
}

// ---------- main ----------
async function run() {
  const brokers = selectedBrokers();
  const kws = $("kws").value.split(/[,\n]/).map((s) => s.trim()).filter(Boolean);
  if (!kws.length) { log("enter at least one keyword", "warn"); $("kws").focus(); return; }
  $("go").disabled = true;
  log(`run  [${brokers.map((b) => NAMES[b]).join(" + ")}]  ${kws.length} keyword(s)`);
  try {
    for (const kw of kws) {
      renderBlock(kw, brokers, null);
      if (brokers.includes("groww")) {
        try { await captureGroww(kw); } catch (e) { log(`groww  "${kw}"  failed: ${e.message || e}`, "err"); }
      }
      try {
        const data = await (await fetch(`${BASE}/api/search?keyword=${encodeURIComponent(kw)}`)).json();
        if (brokers.includes("angelone")) log(`angel  "${kw}"  ${data.angelone.rows.length} rows (${data.angelone.source})`, "ok");
        renderBlock(kw, brokers, data);
      } catch (e) {
        log(`backend unreachable at ${BASE} — is python run.py running?`, "err");
        renderBlock(kw, brokers, Object.fromEntries(brokers.map((b) => [b, { source: "error", error: "backend not reachable", rows: [] }])));
      }
      await sleep(400);
    }
    log("done", "ok");
  } finally {
    $("go").disabled = false;
  }
}
$("go").addEventListener("click", run);
$("search-form").addEventListener("submit", (e) => { e.preventDefault(); run(); });
$("clear").addEventListener("click", () => { $("results").innerHTML = ""; $("log").innerHTML = '<span class="muted">cleared.</span>'; logStarted = false; });
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); $("kws").focus(); }
});
