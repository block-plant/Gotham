"""
Rich node feature builder — replaces the old one-hot-only approach.

Feature vector (16 dimensions per node):
  [0-6]  Node type one-hot  (FIR, Person, Phone, Vehicle, Law, Location, Weapon/Other)
  [7]    Log-degree          (log1p(degree) / log1p(max_degree)) — connectivity signal
  [8]    Degree percentile   (0→1, high = hub / gang leader / shared phone)
  [9]    Multi-FIR flag      (1 if node appears in >1 FIR — recidivist / repeat location)
  [10]   Crime severity      (mean BNS section number / 500, clamped 0→1)
  [11]   Co-accused density  (mean number of other persons per shared FIR, normalized)
  [12]   Name hash dim-0     ┐
  [13]   Name hash dim-1     ├ stable float fingerprint from SHA-256 of node name
  [14]   Name hash dim-2     ┘   gives every node a unique identity the model can learn
  [15]   Reserved / zero

Why name hashing?
  Without it every PERSON node feeds [0,0,0,0,0,0,1,0] to the GNN — they are
  indistinguishable. The model then collapses all persons in the same connected
  component to a single embedding (the "100% for everyone" bug).
  A 3-float SHA-256 hash costs nothing at runtime and uniquely fingerprints
  each node so the GAT can learn individual criminal identity.
"""

import hashlib
import json
import os
import re
import struct
from collections import defaultdict

import lmdb
import numpy as np

FEATURE_DIM = 16

# ── Regex patterns for node type inference ────────────────────────────────────
_RE_FIR      = re.compile(r"^FIR-\d{6}$")
_RE_PID      = re.compile(r"^P_[0-9a-f]{12}$")
_RE_PHONE    = re.compile(r"^(?:\+91[\-\s]?)?[6-9]\d{9}$")
_RE_VEHICLE  = re.compile(r"^[A-Z]{2}[\-\s]?\d{1,2}[\-\s]?[A-Z]{1,2}[\-\s]?\d{4}$")
_RE_LAW      = re.compile(r"(BNS|IPC|NDPS|Arms Act)", re.I)
_LOC_TOKENS  = ("Road", "Sector", "Junction", "Area", "Market",
                "Station", "Alley", "Nagar", "Chowk", "Gate", "Colony")
_RE_BNS_NUM  = re.compile(r"(?:BNS|IPC)\s*(\d+)", re.I)

NODE_TYPES = {
    "fir": 0,
    "pid": 1,       # anonymized person ID  P_xxxx
    "phone": 2,
    "vehicle": 3,
    "law": 4,
    "location": 5,
    "weapon": 6,
    "other": 6,     # catch-all maps to weapon slot (7th one-hot position)
}


def _node_type(label: str) -> int:
    if label is None:
        return 6
    if _RE_FIR.match(label) or label.startswith("UNKNOWN_FIR"):
        return 0
    if _RE_PID.match(label):
        return 1
    if _RE_PHONE.match(label):
        return 2
    if _RE_VEHICLE.match(label):
        return 3
    if _RE_LAW.search(label):
        return 4
    if any(t in label for t in _LOC_TOKENS):
        return 5
    return 6


def _name_hash(label: str):
    """Return 3 stable floats in [0, 1) derived from SHA-256 of the node name."""
    digest = hashlib.sha256(label.encode("utf-8")).digest()
    # Take 3 non-overlapping 4-byte windows → 3 uint32 → scale to [0,1)
    a = struct.unpack(">I", digest[0:4])[0]
    b = struct.unpack(">I", digest[4:8])[0]
    c = struct.unpack(">I", digest[8:12])[0]
    scale = 2**32
    return a / scale, b / scale, c / scale


# ── Statistics gathered from the JSONL ───────────────────────────────────────

def _gather_jsonl_stats(jsonl_path: str, name_to_id: dict) -> dict:
    """
    Single streaming pass over extracted_graph_nodes.jsonl.
    Returns per-node stats dict keyed by row ID:
      fir_count      — how many distinct FIRs this node appeared in
      bns_scores     — list of BNS section numbers seen in those FIRs
      coaccused_sum  — total co-person count across FIRs
      coaccused_n    — number of FIRs contributing to co-accused count
    """
    stats = defaultdict(lambda: {
        "fir_count": 0,
        "bns_scores": [],
        "coaccused_sum": 0,
        "coaccused_n": 0,
    })

    print("  Pass 1/2 — scanning JSONL for per-node statistics …")
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            entities = rec.get("entities", {})

            # Collect BNS section numbers for this FIR
            bns_in_fir = []
            for sec in entities.get("legal_sections", []):
                m = _RE_BNS_NUM.search(sec)
                if m:
                    bns_in_fir.append(int(m.group(1)))

            # Collect all entity strings that appear in this FIR
            all_ents = []
            for cat_items in entities.values():
                all_ents.extend(cat_items)

            # Count unique persons in this FIR (for co-accused signal)
            persons_in_fir = len(entities.get("persons", [])) + \
                             len(entities.get("person_ids", []))

            for ent in all_ents:
                nid = name_to_id.get(ent)
                if nid is None:
                    continue
                s = stats[nid]
                s["fir_count"] += 1
                s["bns_scores"].extend(bns_in_fir)
                if persons_in_fir > 1:
                    s["coaccused_sum"] += persons_in_fir - 1
                    s["coaccused_n"]   += 1

            if line_idx % 10_000 == 0 and line_idx:
                print(f"    {line_idx:,} FIRs scanned …")

    return stats


# ── Degree computation from binary edges ─────────────────────────────────────

def _compute_degrees(tensor_dir: str, node_count: int) -> np.ndarray:
    print("  Pass 2/2 — computing node degrees from edge binaries …")
    meta_path = os.path.join(tensor_dir, "graph_meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    edge_count = meta["edge_count"]

    src_mm = np.memmap(os.path.join(tensor_dir, "edge_src.bin"),
                       dtype=np.int64, mode="r", shape=(edge_count,))
    dst_mm = np.memmap(os.path.join(tensor_dir, "edge_dst.bin"),
                       dtype=np.int64, mode="r", shape=(edge_count,))

    degree = np.zeros(node_count, dtype=np.int64)
    # Count in-degree + out-degree for each valid edge
    chunk = 2_000_000
    for start in range(0, edge_count, chunk):
        end = min(start + chunk, edge_count)
        s = src_mm[start:end]
        d = dst_mm[start:end]
        valid = (s < node_count) & (d < node_count) & (s >= 0) & (d >= 0)
        np.add.at(degree, s[valid], 1)
        np.add.at(degree, d[valid], 1)

    return degree


# ── Main builder ──────────────────────────────────────────────────────────────

def build_node_features(
    jsonl_path: str = "extracted_graph_nodes.jsonl",
    tensor_dir: str = "graph_tensors",
    feature_dim: int = FEATURE_DIM,
):
    os.makedirs(tensor_dir, exist_ok=True)

    # Load graph meta
    with open(os.path.join(tensor_dir, "graph_meta.json")) as f:
        meta = json.load(f)
    node_count = meta["node_count"]

    print(f"Building rich {feature_dim}-dim features for {node_count:,} nodes …")

    # ── Load LMDB name→id map into RAM (needed for JSONL scan) ───────────────
    print("  Loading node mapping …")
    env = lmdb.open(os.path.join(tensor_dir, "node_mapping.lmdb"),
                    readonly=True, lock=False)
    name_to_id = {}
    id_to_name = {}
    with env.begin() as txn:
        for k, v in txn.cursor():
            name   = k.decode("utf-8")
            row_id = struct.unpack(">q", v)[0]
            name_to_id[name]   = row_id
            id_to_name[row_id] = name
    env.close()
    print(f"  Loaded {len(name_to_id):,} node names.")

    # ── Gather per-node statistics from JSONL ─────────────────────────────────
    stats = _gather_jsonl_stats(jsonl_path, name_to_id)

    # ── Compute degree from binary edge arrays ────────────────────────────────
    degree = _compute_degrees(tensor_dir, node_count)

    max_degree   = float(max(degree.max(), 1))
    log_max_deg  = float(np.log1p(max_degree))
    # Percentile thresholds for degree
    deg_sorted   = np.sort(degree)
    p90          = float(deg_sorted[int(0.90 * node_count)])
    p99          = float(deg_sorted[int(0.99 * node_count)])

    # ── Write feature matrix ──────────────────────────────────────────────────
    feat_path = os.path.join(tensor_dir, "node_features.bin")
    features  = np.memmap(feat_path, dtype=np.float32, mode="w+",
                          shape=(node_count, feature_dim))
    features[:] = 0.0

    print(f"  Writing feature matrix ({node_count:,} × {feature_dim}) …")
    for row_id in range(node_count):
        label  = id_to_name.get(row_id, "")
        ntype  = _node_type(label)
        h0, h1, h2 = _name_hash(label)

        deg    = float(degree[row_id])
        s      = stats.get(row_id, {})
        fc     = s.get("fir_count", 0)

        bns_list = s.get("bns_scores", [])
        severity = (float(np.mean(bns_list)) / 500.0) if bns_list else 0.0
        severity = min(severity, 1.0)

        ca_n   = s.get("coaccused_n", 0)
        ca_avg = (s.get("coaccused_sum", 0) / ca_n) if ca_n else 0.0
        ca_norm = min(ca_avg / 10.0, 1.0)   # normalise: 10 co-accused = 1.0

        # [0-6] one-hot type
        features[row_id, ntype] = 1.0
        # [7]  log-degree
        features[row_id, 7]  = float(np.log1p(deg)) / log_max_deg if log_max_deg else 0.0
        # [8]  degree percentile (0→1 scale, p99 maps to 1.0)
        features[row_id, 8]  = min(deg / max(p99, 1.0), 1.0)
        # [9]  multi-FIR recidivist flag
        features[row_id, 9]  = 1.0 if fc > 1 else 0.0
        # [10] crime severity
        features[row_id, 10] = severity
        # [11] co-accused density
        features[row_id, 11] = ca_norm
        # [12-14] name hash fingerprint
        features[row_id, 12] = h0
        features[row_id, 13] = h1
        features[row_id, 14] = h2
        # [15] reserved

    features.flush()

    # Update graph_meta with new feature dim so downstream scripts pick it up
    meta["num_features"] = feature_dim
    with open(os.path.join(tensor_dir, "graph_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✓ Feature matrix saved → {feat_path}")
    print(f"  Shape : {node_count:,} nodes × {feature_dim} dims")
    print(f"  Degree stats: mean={degree.mean():.1f}, max={int(max_degree)}, p90={int(p90)}, p99={int(p99)}")
    print(f"  Unique feature vectors (sample 1000): ", end="")
    sample = np.array(features[:min(1000, node_count)])
    print(len(np.unique(sample, axis=0)))
    return feat_path


if __name__ == "__main__":
    build_node_features()
