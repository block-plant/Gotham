// ─── Config ────────────────────────────────────────────────────────────────────
let CONFIG = {
  url: localStorage.getItem("gotham_url") || "http://localhost:3001",
  key: localStorage.getItem("gotham_key") || "gotham-secret-key-change-in-production",
};

// Tracks the FIR IDs returned from the last Query FIR search
let lastQueryFirIds = [];

// ─── Tab Switching ─────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.getElementById("queryForm").style.display = tab === "query" ? "block" : "none";
  document.getElementById("gangForm").style.display  = tab === "gang"  ? "block" : "none";
  document.getElementById("tabQuery").classList.toggle("active", tab === "query");
  document.getElementById("tabGang").classList.toggle("active",  tab === "gang");
  clearResults();
}

// ─── Config Modal ──────────────────────────────────────────────────────────────
function closeConfig(e) {
  if (e.target.id === "configModal") e.target.style.display = "none";
}
function saveConfig() {
  CONFIG.url = document.getElementById("configUrl").value.trim().replace(/\/$/, "");
  CONFIG.key = document.getElementById("configKey").value.trim();
  localStorage.setItem("gotham_url", CONFIG.url);
  localStorage.setItem("gotham_key", CONFIG.key);
  document.getElementById("configModal").style.display = "none";
  testConnection();
}

// ─── Connection Test ──────────────────────────────────────────────────────────
async function testConnection() {
  const pill = document.getElementById("statusPill");
  pill.textContent = "● CONNECTING...";
  pill.className = "status-pill";
  try {
    const res = await fetch(`${CONFIG.url}/health`, { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      pill.textContent = "● SYSTEM ONLINE";
      pill.className = "status-pill online";
    } else {
      throw new Error("Non-OK response");
    }
  } catch {
    pill.textContent = "● SYSTEM OFFLINE";
    pill.className = "status-pill";
  }
}

// ─── Submit: Query FIR ────────────────────────────────────────────────────────
async function submitQuery(e) {
  e.preventDefault();
  const formData = new FormData(e.target);
  const payload = {};
  for (const [key, val] of formData.entries()) {
    if (val && val.toString().trim()) payload[key] = val.toString().trim();
  }

  if (Object.keys(payload).length === 0) {
    showError("Please fill at least one field before running an investigation.");
    return;
  }

  const threshold = parseInt(document.getElementById("threshold").value || "0", 10) / 100;

  setLoading(true);
  clearResults();
  showLoader("Running GNN investigation...");

  try {
    const res = await fetch(`${CONFIG.url}/api/fir/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": CONFIG.key },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(120_000), // model can take ~2min
    });
    const data = await res.json();
    if (!res.ok || data.status === "error") {
      throw new Error(data.message || "Unknown server error");
    }
    renderQueryResults(data, threshold);
  } catch (err) {
    showError(`Request failed: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

// ─── Submit: Gang Evaluation ──────────────────────────────────────────────────
async function submitGang(e) {
  e.preventDefault();
  const rawIds = document.getElementById("gangFirIds").value.trim();
  const firIds = rawIds.split(",").map(s => s.trim()).filter(Boolean);
  if (firIds.length < 2) {
    showError("Enter at least 2 FIR IDs separated by commas.");
    return;
  }

  const threshold = parseInt(document.getElementById("gangThreshold").value || "0", 10) / 100;

  setLoading(true);
  clearResults();
  showLoader(`Evaluating ${firIds.length} FIRs for hidden syndicate links...`);

  try {
    const res = await fetch(`${CONFIG.url}/api/fir/gang`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": CONFIG.key },
      body: JSON.stringify({ fir_ids: firIds, threshold }),
      signal: AbortSignal.timeout(120_000),
    });
    const data = await res.json();
    if (!res.ok || data.status === "error") {
      throw new Error(data.message || "Unknown server error");
    }
    renderGangResults(data);
  } catch (err) {
    showError(`Request failed: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

// ─── Render: FIR Query Results ────────────────────────────────────────────────
function renderQueryResults(data, threshold) {
  const list = document.getElementById("resultsList");
  list.innerHTML = "";

  // Entity summary
  const summary = document.getElementById("entitySummary");
  const matchedEl = document.getElementById("matchedEntities");
  const unmatchedEl = document.getElementById("unmatchedEntities");
  summary.style.display = "none";

  if (data.matched_entities?.length || data.unmatched_fields?.length) {
    summary.style.display = "flex";
    if (data.matched_entities?.length) {
      matchedEl.style.display = "block";
      matchedEl.innerHTML = `[MATCH] Matched in graph:<br>${data.matched_entities.map(e => `&nbsp;&nbsp;• ${e}`).join("<br>")}`;
    } else { matchedEl.style.display = "none"; }

    if (data.unmatched_fields?.length) {
      unmatchedEl.style.display = "block";
      unmatchedEl.innerHTML = `[WARN] Not found in graph:<br>${data.unmatched_fields.map(e => `&nbsp;&nbsp;• ${e}`).join("<br>")}`;
    } else { unmatchedEl.style.display = "none"; }
  }

  const results = (data.results || []).filter(r => r.probability >= threshold);
  lastQueryFirIds = results.map(r => r.fir_id); // store for gang eval

  document.getElementById("resultsSub").textContent =
    `${results.length} linked records found (threshold: ${Math.round(threshold * 100)}%)`;

  if (results.length === 0) {
    list.innerHTML = `<div class="empty-state">
      <p>No links found above ${Math.round(threshold * 100)}% threshold.</p>
      <p class="empty-hint">Try lowering the threshold or providing more FIR fields.</p>
    </div>`;
    return;
  }

  // ── Master: Evaluate all results as a gang ────────────────────────────
  if (results.length >= 2) {
    const gangBtn = document.createElement("button");
    gangBtn.className = "btn-gang-eval";
    gangBtn.textContent = `EVALUATE ALL ${results.length} RESULTS AS GANG`;
    gangBtn.onclick = evaluateAsGang;
    list.appendChild(gangBtn);
  }

  for (const r of results) {
    list.appendChild(buildResultCard(r.fir_id, r.probability, r.evidence));
  }
}

// ─── Render: Gang Results ─────────────────────────────────────────────────────
function renderGangResults(data) {
  const list = document.getElementById("resultsList");
  list.innerHTML = "";

  const pairs = data.pairs || [];
  document.getElementById("resultsSub").textContent =
    `${pairs.length} FIR pair(s) evaluated for hidden syndicate links`;

  if (data.unrecognized_firs?.length) {
    const warn = document.createElement("div");
    warn.className = "error-banner";
    warn.style.borderColor = "var(--yellow)";
    warn.style.color = "var(--yellow)";
    warn.style.background = "#fff8dc";
    warn.textContent = `[WARN] Unrecognized FIR IDs: ${data.unrecognized_firs.join(", ")}`;
    list.appendChild(warn);
  }

  if (pairs.length === 0) {
    list.innerHTML += `<div class="empty-state">
      <p>No links found above threshold.</p></div>`;
    return;
  }

  for (const p of pairs) {
    const card = document.createElement("div");
    card.className = "pair-card";
    const [cls, label] = probClass(p.probability);
    const pct = (p.probability * 100).toFixed(1);

    const evTags = (p.evidence || ["Network proximity only"]).map(ev => {
      const isNetworkOnly = ev.toLowerCase().includes("network");
      return `<span class="ev-tag${isNetworkOnly ? " network-prox" : ""}">${ev}</span>`;
    }).join("");

    card.innerHTML = `
      <div class="pair-card-bar ${cls}"></div>
      <div class="pair-body">
        <div class="pair-firs-row">
          <span class="pair-fir-id">${p.fir_a}</span>
          <span class="pair-link-arrow">&#8596;</span>
          <span class="pair-fir-id">${p.fir_b}</span>
        </div>
        <div class="pair-prob-block">
          <div>
            <div class="pair-prob-label">Link Probability</div>
            <div class="pair-prob-value ${cls}">${pct}%</div>
          </div>
          <span class="pair-confidence-label ${cls}">${label} CONFIDENCE</span>
        </div>
        <div class="pair-evidence-section">
          <div class="pair-evidence-title">Evidence Factors</div>
          <div class="pair-evidence-tags">${evTags}</div>
        </div>
      </div>`;
    list.appendChild(card);
  }
}

// ─── Build a Result Card ──────────────────────────────────────────────────────
function buildResultCard(firId, prob, evidence) {
  const card = document.createElement("div");
  card.className = "result-card";

  const [cls, label] = probClass(prob);

  card.innerHTML = `
    <div class="result-header" onclick="toggleCard(this.parentElement)">
      <span class="fir-id">${firId}</span>
      <span class="prob-badge ${cls}">${label} ${(prob * 100).toFixed(1)}%</span>
      <span class="chevron">&#9660;</span>
    </div>
    <div class="result-body">
      <ul class="evidence-list">
        ${(evidence || ["No specific evidence"]).map(ev => `<li>${ev}</li>`).join("")}
      </ul>
      <button class="btn-deep-dive" onclick="deepDive('${firId}')">
        DEEP DIVE: Evaluate this FIR against other results
      </button>
    </div>`;
  return card;
}

// ─── Deep Dive: one result FIR vs the rest ───────────────────────────────────
function deepDive(targetFirId) {
  // Pick the target + top 4 others from the last query results
  const others = lastQueryFirIds.filter(id => id !== targetFirId).slice(0, 4);
  const allIds = [targetFirId, ...others];
  if (allIds.length < 2) {
    showError("Not enough FIR results to run a deep dive. Try a broader search.");
    return;
  }
  switchTab("gang");
  document.getElementById("gangFirIds").value = allIds.join(", ");
  document.getElementById("gangThreshold").value = "0";
  document.getElementById("gangForm").dispatchEvent(new Event("submit", { cancelable: true }));
}

// ─── Evaluate All Results as Gang ────────────────────────────────────────────
function evaluateAsGang() {
  if (lastQueryFirIds.length < 2) {
    showError("Need at least 2 results to run gang evaluation.");
    return;
  }
  // Take top 6 to avoid combinatorial explosion (6 FIRs = 15 pairs)
  const ids = lastQueryFirIds.slice(0, 6);
  switchTab("gang");
  document.getElementById("gangFirIds").value = ids.join(", ");
  document.getElementById("gangThreshold").value = "0";
  document.getElementById("gangForm").dispatchEvent(new Event("submit", { cancelable: true }));
}

function toggleCard(card) {
  card.classList.toggle("open");
}

// ─── Probability Color Class ──────────────────────────────────────────────────
function probClass(prob) {
  if (prob >= 0.85) return ["prob-high", "HIGH"];
  if (prob >= 0.50) return ["prob-med",  "MED"];
  return ["prob-low", "LOW"];
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────
function clearResults() {
  document.getElementById("resultsList").innerHTML = "";
  document.getElementById("entitySummary").style.display = "none";
  document.getElementById("resultsSub").textContent = "Submit a FIR to see linked criminal records.";
}

function showLoader(msg) {
  document.getElementById("resultsList").innerHTML = `
    <div class="loader">
      <div class="spinner"></div>
      <span>${msg}</span>
    </div>`;
}

function showError(msg) {
  document.getElementById("resultsList").innerHTML = `
    <div class="error-banner">[ERROR] ${msg}</div>`;
}

function setLoading(loading) {
  document.getElementById("submitBtn").disabled = loading;
  document.getElementById("gangSubmitBtn").disabled = loading;
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.getElementById("configUrl").value = CONFIG.url;
document.getElementById("configKey").value = CONFIG.key;
testConnection();
