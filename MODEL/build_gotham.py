import os
import sys
import json
import random

root_dir = os.path.dirname(os.path.abspath(__file__))
JSONL_PATH = os.path.join(root_dir, "data", "extracted_graph_nodes.jsonl")
OUTPUT_PATH = os.path.join(root_dir, "police_graph_sample.html")

# ─── Node type pastel colors ────────────────────────────────────────
NODE_STYLE = {
    "FIR":      {"bg": "#e2e8f0", "border": "#cbd5e1", "font": "#0f172a", "shape": "box",  "size": 14},
    "DIST":     {"bg": "#fef3c7", "border": "#fde68a", "font": "#78350f", "shape": "dot",  "size": 12},
    "UNIT":     {"bg": "#ffedd5", "border": "#fed7aa", "font": "#9a3412", "shape": "dot",  "size": 10},
    "CG":       {"bg": "#dbeafe", "border": "#bfdbfe", "font": "#1e40af", "shape": "dot",  "size": 13},
    "MO":       {"bg": "#ccfbf1", "border": "#99f6e4", "font": "#0f766e", "shape": "dot",  "size": 10},
    "ACT":      {"bg": "#fee2e2", "border": "#fecaca", "font": "#991b1b", "shape": "dot",  "size": 9},
    "IO":       {"bg": "#d1fae5", "border": "#a7f3d0", "font": "#065f46", "shape": "dot",  "size": 10},
    "BEAT":     {"bg": "#cffafe", "border": "#a5f3fc", "font": "#164e63", "shape": "dot",  "size": 8},
    "AREA":     {"bg": "#ecfccb", "border": "#d9f99d", "font": "#3f6212", "shape": "dot",  "size": 8},
    "GANG":     {"bg": "#ffe4e6", "border": "#fecdd3", "font": "#9f1239", "shape": "diamond", "size": 14},
    "LANDMARK": {"bg": "#fef9c3", "border": "#fef08a", "font": "#92400e", "shape": "dot",  "size": 8},
    "OTHER":    {"bg": "#f1f5f9", "border": "#e2e8f0", "font": "#334155", "shape": "dot",  "size": 8},
}

def get_type(node_id: str) -> str:
    u = node_id.upper()
    if u.startswith("FIR-"):       return "FIR"
    if u.startswith("DIST_"):      return "DIST"
    if u.startswith("UNIT_"):      return "UNIT"
    if u.startswith("CG_"):        return "CG"
    if u.startswith("MO_"):        return "MO"
    if u.startswith("ACT_"):       return "ACT"
    if u.startswith("IO_"):        return "IO"
    if u.startswith("BEAT_"):      return "BEAT"
    if u.startswith("AREA_"):      return "AREA"
    if u.startswith("GANG_"):      return "GANG"
    if u.startswith("LANDMARK_"):  return "LANDMARK"
    return "OTHER"

def clean_label(node_id: str, ntype: str) -> str:
    prefixes = {"FIR": "FIR-", "DIST": "DIST_", "UNIT": "UNIT_", "CG": "CG_",
                "MO": "MO_", "ACT": "ACT_", "IO": "IO_", "BEAT": "BEAT_",
                "AREA": "AREA_", "GANG": "GANG_", "LANDMARK": "LANDMARK_"}
    label = node_id
    p = prefixes.get(ntype)
    if p and label.startswith(p):
        label = label[len(p):]
    return label[:32] + "…" if len(label) > 32 else label

def build_graph(max_firs: int):
    nodes_map = {}
    edges_set = set()
    fir_count = 0
    with open(JSONL_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if fir_count >= max_firs: break
            try: rec = json.loads(line.strip())
            except Exception: continue
            fir_id = rec.get("fir_id")
            if not fir_id: continue
            fir_count += 1
            entities = rec.get("entities", {})
            num_feat = rec.get("numeric_features", {})
            
            def add_edge(src, dst):
                if src and dst and src != dst:
                    edges_set.add(tuple(sorted((src, dst))))
                    if src not in nodes_map: nodes_map[src] = {"id": src, "full_label": src}
                    if dst not in nodes_map: nodes_map[dst] = {"id": dst, "full_label": dst}
            
            if fir_id not in nodes_map: nodes_map[fir_id] = {"id": fir_id, "full_label": fir_id}
            
            for cg in entities.get("crime_groups", []): add_edge(f"CG_{cg}", fir_id)
            for mo in entities.get("crime_heads", []): add_edge(f"MO_{mo}", fir_id)
            for act in entities.get("act_sections", []): add_edge(f"ACT_{act}", fir_id)
            for dist in entities.get("districts", []): add_edge(f"DIST_{dist}", fir_id)
            for unit in entities.get("units", []): add_edge(f"UNIT_{unit}", fir_id)
            for beat in entities.get("beats", []): add_edge(f"BEAT_{beat}", fir_id)
            for area in entities.get("areas", []): add_edge(f"AREA_{area}", fir_id)
            for io_name in entities.get("officers", []): add_edge(f"IO_{io_name}", fir_id)
            for lm in entities.get("landmarks", []): add_edge(f"LANDMARK_{lm}", fir_id)
            
            accused = num_feat.get("accused_count", 1)
            if accused == 1:     gang = "GANG_SOLO"
            elif accused == 2:   gang = "GANG_DUO_2"
            elif accused <= 5:   gang = "GANG_GROUP_3_5"
            else:                gang = "GANG_SYNDICATE_6PLUS"
            add_edge(gang, fir_id)
    return nodes_map, edges_set

def build_vis_nodes(nodes_map):
    out = []
    for nid in nodes_map:
        ntype = get_type(nid)
        s = NODE_STYLE.get(ntype, NODE_STYLE["OTHER"])
        label = clean_label(nid, ntype)
        tooltip = f"<div style='font:12px Inter,sans-serif;padding:6px 10px;max-width:300px;color:#1e293b;background:#ffffff;border-radius:8px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.1)'><b>[{ntype}]</b><br>{nid}</div>"
        out.append({
            "id": nid, "label": label, "title": tooltip, "shape": s["shape"], "size": s["size"],
            "color": {
                "background": s["bg"], "border": s["border"],
                "highlight": {"background": "#ffffff", "border": "#3b82f6"},
                "hover": {"background": "#ffffff", "border": "#3b82f6"}
            },
            "font": {"color": s["font"], "size": 9 if ntype != "FIR" else 10, "face": "Inter"},
            "borderWidth": 1.5
        })
    return out

def build_vis_edges(edges_set):
    out = []
    for i, (src, dst) in enumerate(edges_set):
        out.append({
            "id": i, "from": src, "to": dst,
            "color": {"color": "rgba(148,163,184,0.4)", "highlight": "#3b82f6", "hover": "#3b82f6"},
            "width": 1.0, "hoverWidth": 2.5, "selectionWidth": 2.5
        })
    return out

def build_search_index(nodes_map):
    idx = []
    for nid in nodes_map:
        ntype = get_type(nid)
        idx.append([nid, ntype, clean_label(nid, ntype)])
    return idx

def generate_html():
    max_firs = 200
    nodes_map, edges_set = build_graph(max_firs)
    nodes_vis = build_vis_nodes(nodes_map)
    edges_vis = build_vis_edges(edges_set)
    search_index = build_search_index(nodes_map)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Gotham</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"></script>
  <style>
    :root {{
      --bg-deep: #f8fafc;
      --bg-panel: #ffffff;
      --bg-card: #f1f5f9;
      --bg-hover: #e2e8f0;
      --accent: #2563eb;
      --text: #1e293b;
      --text-muted: #64748b;
      --text-dim: #94a3b8;
      --border: #e2e8f0;
      --radius: 12px;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }}
    * {{box-sizing:border-box;margin:0;padding:0;}}
    body {{font-family:'Inter',sans-serif;background:var(--bg-deep);color:var(--text);height:100vh;overflow:hidden;display:flex;flex-direction:column;}}
    
    header {{
      background: var(--bg-panel);
      border-bottom: 1px solid var(--border);
      padding: 0 24px;
      height: 64px;
      display: flex;
      align-items: center;
      gap: 16px;
      flex-shrink: 0;
      box-shadow: var(--shadow);
      z-index: 10;
    }}
    .logo {{font-size: 20px; font-weight: 700; color: var(--accent); display: flex; align-items: center; gap: 8px;}}
    .logo span {{background: linear-gradient(135deg, #1d4ed8, #0891b2); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}}
    
    .search-wrap {{flex: 1; max-width: 600px; position: relative;}}
    .search-icon {{position: absolute; left: 16px; top: 50%; transform: translateY(-50%); color: var(--text-muted); font-size: 14px;}}
    #searchInput {{width: 100%; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 100px; padding: 10px 16px 10px 42px; font-size: 14px; color: var(--text); outline: none; transition: all 0.2s;}}
    #searchInput:focus {{border-color: var(--accent); background: #ffffff; box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);}}
    
    .stats {{display: flex; gap: 12px; margin-left: auto;}}
    .stat-pill {{padding: 6px 12px; background: #f1f5f9; border-radius: 100px; font-size: 12px; font-weight: 500; color: var(--text-muted); display: flex; align-items: center; gap: 6px;}}
    .stat-pill .dot {{width: 8px; height: 8px; border-radius: 50%;}}
    
    .workspace {{display: flex; flex: 1; overflow: hidden; position: relative;}}
    
    #sidebar {{width: 320px; background: var(--bg-panel); border-right: 1px solid var(--border); display: flex; flex-direction: column; z-index: 5; box-shadow: 2px 0 10px rgba(0,0,0,0.02);}}
    .sidebar-section {{padding: 20px; border-bottom: 1px solid var(--border);}}
    .section-title {{font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 12px;}}
    
    .filters {{display: flex; flex-wrap: wrap; gap: 8px;}}
    .filter-btn {{padding: 6px 12px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 100px; font-size: 12px; color: var(--text-muted); cursor: pointer; transition: all 0.2s; font-weight: 500;}}
    .filter-btn:hover {{background: #f8fafc; border-color: #94a3b8; color: var(--text);}}
    .filter-btn.active {{background: var(--accent); border-color: var(--accent); color: #ffffff; box-shadow: 0 2px 6px rgba(37,99,235,0.3);}}
    
    #infoPanel {{flex: 1; padding: 20px; overflow-y: auto;}}
    .empty-state {{text-align: center; color: var(--text-muted); margin-top: 40px; font-size: 14px;}}
    
    .info-card {{background: var(--bg-deep); border: 1px solid var(--border); border-radius: 16px; padding: 16px; margin-bottom: 16px;}}
    .info-card h3 {{font-size: 15px; font-weight: 600; margin: 10px 0 4px; color: var(--text);}}
    .info-card p {{font-size: 12px; color: var(--text-muted); margin-bottom: 12px;}}
    
    .conn-list {{list-style: none;}}
    .conn-list li {{padding: 8px 12px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 6px; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.2s;}}
    .conn-list li:hover {{border-color: var(--accent); transform: translateX(2px); box-shadow: 0 2px 4px rgba(0,0,0,0.02);}}
    
    #graph-container {{flex: 1; position: relative; background: radial-gradient(circle at center, #ffffff 0%, #f1f5f9 100%);}}
    #network {{width: 100%; height: 100%;}}
    
    .overlay {{position: absolute; inset: 0; background: rgba(255,255,255,0.9); z-index: 100; display: flex; flex-direction: column; align-items: center; justify-content: center; backdrop-filter: blur(4px); transition: opacity 0.5s;}}
    .overlay.hidden {{opacity: 0; pointer-events: none;}}
    .spinner {{width: 48px; height: 48px; border: 4px solid #e2e8f0; border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 16px;}}
    @keyframes spin {{to {{transform: rotate(360deg);}}}}
    .loading-text {{font-size: 14px; font-weight: 500; color: var(--text-muted);}}
    
    .controls {{position: absolute; bottom: 24px; right: 24px; display: flex; gap: 8px; z-index: 10;}}
    .ctrl-btn {{width: 40px; height: 40px; border-radius: 50%; background: #ffffff; border: 1px solid #e2e8f0; box-shadow: var(--shadow); color: var(--text-muted); font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;}}
    .ctrl-btn:hover {{background: #f8fafc; color: var(--accent); transform: translateY(-2px);}}
    
    .dropdown {{position: absolute; top: calc(100% + 8px); left: 0; right: 0; background: #ffffff; border: 1px solid var(--border); border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); max-height: 320px; overflow-y: auto; display: none; z-index: 1000; padding: 8px;}}
    .dropdown.active {{display: block;}}
    .drop-item {{padding: 10px 12px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 13px; transition: all 0.1s;}}
    .drop-item:hover, .drop-item.selected {{background: #f1f5f9;}}
    .drop-item mark {{background: #dbeafe; color: #1d4ed8; border-radius: 4px; padding: 0 2px;}}
    
    .badge {{font-size: 10px; font-weight: 600; padding: 4px 8px; border-radius: 6px; letter-spacing: 0.05em;}}
    .badge-FIR {{background: #f1f5f9; color: #475569;}}
    .badge-CG {{background: #eff6ff; color: #2563eb;}}
    .badge-MO {{background: #ccfbf1; color: #0f766e;}}
    .badge-ACT {{background: #fef2f2; color: #dc2626;}}
    .badge-IO {{background: #ecfdf5; color: #059669;}}
    .badge-DIST, .badge-UNIT {{background: #fffbeb; color: #d97706;}}
    .badge-BEAT, .badge-AREA {{background: #ecfeff; color: #0891b2;}}
    .badge-GANG {{background: #fff1f2; color: #e11d48;}}
    .badge-LANDMARK {{background: #fef9c3; color: #92400e;}}
  </style>
</head>
<body>

<header>
  <div class="logo">🦇 <span>Gotham</span></div>
  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input type="text" id="searchInput" placeholder="Search for cases, officers, locations, gangs..." autocomplete="off"/>
    <div class="dropdown" id="searchDropdown"></div>
  </div>
  <div class="stats">
    <div class="stat-pill"><div class="dot" style="background: #3b82f6"></div> {len(nodes_vis)} Nodes</div>
    <div class="stat-pill"><div class="dot" style="background: #0891b2"></div> {len(edges_vis)} Connections</div>
    <div class="stat-pill"><div class="dot" style="background: #10b981"></div> {max_firs} FIRs</div>
  </div>
</header>

<div class="workspace">
  <aside id="sidebar">
    <div class="sidebar-section">
      <div class="section-title">Filter by Entity Type</div>
      <div class="filters" id="filters">
        <button class="filter-btn active" data-type="ALL">All Entities</button>
        <button class="filter-btn" data-type="FIR">Case / FIR</button>
        <button class="filter-btn" data-type="CG">Crime Group</button>
        <button class="filter-btn" data-type="MO">Modus Operandi</button>
        <button class="filter-btn" data-type="ACT">Statute</button>
        <button class="filter-btn" data-type="IO">Officer (IO)</button>
        <button class="filter-btn" data-type="DIST">District & Unit</button>
        <button class="filter-btn" data-type="BEAT">Beat & Area</button>
        <button class="filter-btn" data-type="GANG">Gang Pattern</button>
      </div>
    </div>
    <div id="infoPanel">
      <div class="empty-state">
        <div style="font-size: 32px; margin-bottom: 12px; opacity: 0.5;">🔎</div>
        Select any node on the graph or<br>search to start your investigation.
      </div>
    </div>
  </aside>
  
  <div id="graph-container">
    <div class="overlay" id="loader">
      <div class="spinner"></div>
      <div class="loading-text">Gotham AI is assembling {max_firs} cases...</div>
    </div>
    <div id="network"></div>
    <div class="controls">
      <button class="ctrl-btn" id="btnZoomIn" title="Zoom In">+</button>
      <button class="ctrl-btn" id="btnZoomOut" title="Zoom Out">−</button>
      <button class="ctrl-btn" id="btnFit" title="Fit to Screen">⛶</button>
    </div>
  </div>
</div>

<script>
const nodes = new vis.DataSet({json.dumps(nodes_vis, separators=(',', ':'))});
const edges = new vis.DataSet({json.dumps(edges_vis, separators=(',', ':'))});
const searchIndex = {json.dumps(search_index, separators=(',', ':'))};

const container = document.getElementById('network');
const data = {{ nodes: nodes, edges: edges }};
const options = {{
  physics: {{
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {{ gravitationalConstant: -35, centralGravity: 0.005, springLength: 90, springConstant: 0.05, damping: 0.6, avoidOverlap: 0.5 }},
    stabilization: {{ iterations: 150, updateInterval: 25 }},
    maxVelocity: 50, minVelocity: 0.1
  }},
  interaction: {{ hover: true, tooltipDelay: 150, zoomView: true, dragView: true, multiselect: true }},
  edges: {{ smooth: {{ type: 'continuous', roundness: 0.2 }} }},
  nodes: {{ scaling: {{ min: 10, max: 25 }} }}
}};

const network = new vis.Network(container, data, options);

network.on('stabilizationIterationsDone', () => {{
  document.getElementById('loader').classList.add('hidden');
  network.setOptions({{ physics: {{ enabled: false }} }});
}});

// Adjacency mapping
const adj = {{}};
edges.get().forEach(e => {{
  (adj[e.from] = adj[e.from] || []).push(e.to);
  (adj[e.to] = adj[e.to] || []).push(e.from);
}});

// Info Panel updating
function getType(nid) {{
  const match = searchIndex.find(x => x[0] === nid);
  return match ? match[1] : 'OTHER';
}}
function getShort(nid) {{
  const match = searchIndex.find(x => x[0] === nid);
  return match ? match[2] : nid;
}}

network.on('click', p => {{
  if(p.nodes.length > 0) showNode(p.nodes[0]);
  else resetSelection();
}});

function showNode(nid) {{
  const neighbors = [...new Set(adj[nid] || [])];
  
  // Highlight
  const highlight = new Set([nid, ...neighbors]);
  nodes.update(nodes.get().map(n => ({{ id: n.id, opacity: highlight.has(n.id) ? 1 : 0.15 }})));
  edges.update(edges.get().map(e => ({{ id: e.id, 
    color: {{ color: (e.from===nid || e.to===nid) ? 'rgba(37,99,235,0.8)' : 'rgba(148,163,184,0.1)' }},
    width: (e.from===nid || e.to===nid) ? 2.5 : 0.5
  }})));
  network.focus(nid, {{ scale: 1.2, animation: {{ duration: 400, easingFunction: 'easeInOutQuad' }} }});
  
  // Update sidebar
  const type = getType(nid);
  let html = `
    <div class="info-card">
      <span class="badge badge-${{type}}">${{type}}</span>
      <h3>${{getShort(nid)}}</h3>
      <p>Node ID: ${{nid}}</p>
      <div style="font-size:12px; font-weight:500; color:var(--text); margin-top:12px;">
        ${{neighbors.length}} Connected Entities
      </div>
    </div>
    <div class="section-title">Direct Connections</div>
    <ul class="conn-list">
  `;
  
  neighbors.slice(0, 40).forEach(nb => {{
    const ntype = getType(nb);
    html += `
      <li onclick="showNode('${{nb.replace(/'/g,"\\'") }}')">
        <span class="badge badge-${{ntype}}">${{ntype}}</span>
        <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${{getShort(nb)}}</span>
      </li>
    `;
  }});
  if(neighbors.length > 40) html += `<li style="justify-content:center;color:#94a3b8;border:none;background:transparent">+${{neighbors.length - 40}} more</li>`;
  html += `</ul>`;
  
  document.getElementById('infoPanel').innerHTML = html;
}}

function resetSelection() {{
  nodes.update(nodes.get().map(n => ({{ id: n.id, opacity: 1 }})));
  edges.update(edges.get().map(e => ({{ id: e.id, color: {{ color: 'rgba(148,163,184,0.4)' }}, width: 1.0 }})));
  document.getElementById('infoPanel').innerHTML = `
    <div class="empty-state">
      <div style="font-size: 32px; margin-bottom: 12px; opacity: 0.5;">🔎</div>
      Select any node on the graph or<br>search to start your investigation.
    </div>
  `;
}}

// Search Logic
const searchInput = document.getElementById('searchInput');
const dropdown = document.getElementById('searchDropdown');
let selIdx = -1;

function highlightStr(text, query) {{
  const tokens = query.toLowerCase().split(/\\s+/).filter(Boolean);
  let res = text;
  tokens.forEach(t => {{
    res = res.replace(new RegExp(t.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&'), 'gi'), m => `<mark>${{m}}</mark>`);
  }});
  return res;
}}

searchInput.addEventListener('input', e => {{
  const q = e.target.value.trim().toLowerCase();
  if(!q) {{ dropdown.classList.remove('active'); return; }}
  
  const tokens = q.split(/\\s+/).filter(Boolean);
  const results = searchIndex.filter(r => tokens.every(t => (r[0]+' '+r[2]).toLowerCase().includes(t))).slice(0, 15);
  
  if(results.length === 0) {{
    dropdown.innerHTML = `<div class="drop-item" style="color:#94a3b8; justify-content:center;">No results found</div>`;
  }} else {{
    dropdown.innerHTML = results.map((r, i) => `
      <div class="drop-item" data-id="${{r[0]}}" data-idx="${{i}}">
        <span class="badge badge-${{r[1]}}">${{r[1]}}</span>
        <span>${{highlightStr(r[2] || r[0], q)}}</span>
      </div>
    `).join('');
    dropdown.querySelectorAll('.drop-item').forEach(el => el.addEventListener('click', () => {{
      dropdown.classList.remove('active'); searchInput.value = ''; showNode(el.dataset.id);
    }}));
  }}
  dropdown.classList.add('active');
  selIdx = -1;
}});

searchInput.addEventListener('keydown', e => {{
  const items = dropdown.querySelectorAll('.drop-item');
  if(e.key === 'ArrowDown') {{ e.preventDefault(); selIdx = Math.min(selIdx+1, items.length-1); }}
  else if(e.key === 'ArrowUp') {{ e.preventDefault(); selIdx = Math.max(selIdx-1, -1); }}
  else if(e.key === 'Enter') {{
    if(selIdx >= 0 && items[selIdx]) items[selIdx].click();
    else if(items.length > 0) items[0].click();
  }}
  else if(e.key === 'Escape') {{ dropdown.classList.remove('active'); searchInput.blur(); }}
  items.forEach((el, i) => el.classList.toggle('selected', i === selIdx));
}});
document.addEventListener('click', e => {{ if(!e.target.closest('.search-wrap')) dropdown.classList.remove('active'); }});

// Filters
document.getElementById('filters').addEventListener('click', e => {{
  if(!e.target.classList.contains('filter-btn')) return;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');
  
  const type = e.target.dataset.type;
  if(type === 'ALL') {{
    nodes.update(nodes.get().map(n => ({{ id: n.id, opacity: 1 }})));
    edges.update(edges.get().map(e => ({{ id: e.id, color: {{ color: 'rgba(148,163,184,0.4)' }}, width: 1.0 }})));
  }} else {{
    const match = new Set(searchIndex.filter(r => r[1] === type || (type==='DIST' && r[1]==='UNIT') || (type==='BEAT' && r[1]==='AREA')).map(r => r[0]));
    nodes.update(nodes.get().map(n => ({{ id: n.id, opacity: match.has(n.id) ? 1 : 0.05 }})));
    edges.update(edges.get().map(e => ({{ id: e.id, 
      color: {{ color: (match.has(e.from) || match.has(e.to)) ? 'rgba(37,99,235,0.6)' : 'rgba(148,163,184,0.05)' }},
      width: (match.has(e.from) || match.has(e.to)) ? 1.5 : 0.2
    }})));
  }}
}});

// Zoom Controls
document.getElementById('btnZoomIn').addEventListener('click', () => network.moveTo({{ scale: network.getScale() * 1.3, animation: {{duration: 200}} }}));
document.getElementById('btnZoomOut').addEventListener('click', () => network.moveTo({{ scale: network.getScale() * 0.77, animation: {{duration: 200}} }}));
document.getElementById('btnFit').addEventListener('click', () => network.fit({{ animation: {{duration: 400}} }}));

</script>
</body>
</html>
"""
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Graph with {max_firs} FIRs generated to {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_html()
