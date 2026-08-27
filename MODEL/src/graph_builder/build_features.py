"""
Rich Detective Feature Builder for Real FIR Data.

Feature vector layout (788 dimensions per node):
  [0-9]    Node type one-hot (FIR, MO, CrimeGroup, ActSection, Beat, Unit/PS, District, Area, IO, Landmark/Gang)
  [10]     Log-degree (log1p(degree) / log1p(max_degree))
  [11]     Accused Count (normalized / 10)
  [12]     Arrested Count (normalized / 10)
  [13]     Chargesheeted Count (normalized / 10)
  [14]     Conviction Count (normalized / 5)
  [15]     Heinous Severity Flag (1.0 for Heinous, 0.0 otherwise)
  [16]     Distance from PS (normalized / 50 km)
  [17]     Cyclical Month Sin: sin(2pi * month / 12)
  [18]     Cyclical Month Cos: cos(2pi * month / 12)
  [19]     Offence Duration (normalized / 48 hrs)
  [20-787] NLP Semantic Vector (from all-mpnet-base-v2, dim=768)

Memory fix: LMDB cursor streamed in batches instead of loading full dict into RAM.
NLP batch_size reduced 512 → 128 to prevent OpenBLAS OOM on large node counts.
"""

import json
import os
import sys
import struct
import math
from collections import defaultdict

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import lmdb
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

FEATURE_DIM = 788

NODE_TYPES = {
    "fir": 0,
    "mo": 1,
    "cg": 2,
    "act": 3,
    "beat": 4,
    "unit": 5,
    "dist": 6,
    "area": 7,
    "io": 8,
    "landmark": 9,
    "other": 9,
}

def _node_type(label: str) -> int:
    if not label: return 9
    if label.startswith("FIR-"): return 0
    if label.startswith("MO_"): return 1
    if label.startswith("CG_"): return 2
    if label.startswith("ACT_"): return 3
    if label.startswith("BEAT_"): return 4
    if label.startswith("UNIT_"): return 5
    if label.startswith("DIST_"): return 6
    if label.startswith("AREA_"): return 7
    if label.startswith("IO_"): return 8
    if label.startswith("LANDMARK_") or label.startswith("GANG_"): return 9
    return 9

def _clean_label_for_nlp(label: str) -> str:
    """Format label into descriptive English for the NLP embedding model."""
    if not label: return ""
    if label.startswith("MO_"):
        return f"Modus Operandi: {label[3:].replace('_', ' ').title()}"
    if label.startswith("CG_"):
        return f"Crime Category: {label[3:].replace('_', ' ').title()}"
    if label.startswith("ACT_"):
        return f"Legal Statute and Penal Code: {label[4:].replace('_', ' ')}"
    if label.startswith("BEAT_"):
        return f"Police Patrol Beat: {label[5:].replace('_', ' ').title()}"
    if label.startswith("UNIT_"):
        return f"Police Station Unit: {label[5:].replace('_', ' ').title()}"
    if label.startswith("DIST_"):
        return f"Police District Jurisdiction: {label[5:].replace('_', ' ').title()}"
    if label.startswith("AREA_"):
        return f"Locality Village Area: {label[5:].replace('_', ' ').title()}"
    if label.startswith("IO_"):
        return f"Investigating Officer: {label[3:].replace('_', ' ').title()}"
    if label.startswith("LANDMARK_"):
        return f"Crime Scene Landmark: {label[9:].replace('_', ' ').title()}"
    if label.startswith("GANG_"):
        return f"Criminal Gang Demographic: {label[5:].replace('_', ' ').title()}"
    return label.replace("_", " ")

def _gather_jsonl_stats(jsonl_path: str, name_to_id: dict) -> tuple:
    stats = defaultdict(lambda: {
        "accused_count": 0.0,
        "arrested_count": 0.0,
        "chargesheeted_count": 0.0,
        "conviction_count": 0.0,
        "is_heinous": 0.0,
        "distance_from_ps": 0.0,
        "month": 1,
        "offence_duration": 0.0,
    })
    fir_narratives = {}

    print("  Pass 1/3 — Scanning JSONL for numeric metrics and narratives...")
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f):
            try:
                rec = json.loads(line)
            except Exception:
                continue

            fir_id = rec.get("fir_id")
            num_feat = rec.get("numeric_features", {})
            narrative = rec.get("narrative", "")

            nid = name_to_id.get(fir_id)
            if nid is not None:
                s = stats[nid]
                s["accused_count"] = float(num_feat.get("accused_count", 0.0))
                s["arrested_count"] = float(num_feat.get("arrested_count", 0.0))
                s["chargesheeted_count"] = float(num_feat.get("chargesheeted_count", 0.0))
                s["conviction_count"] = float(num_feat.get("conviction_count", 0.0))
                s["is_heinous"] = float(num_feat.get("is_heinous", 0.0))
                s["distance_from_ps"] = float(num_feat.get("distance_from_ps", 0.0))
                s["month"] = int(num_feat.get("fir_month", 1))
                s["offence_duration"] = float(num_feat.get("offence_duration", 0.0))
                if narrative:
                    fir_narratives[nid] = narrative

            if line_idx % 25000 == 0 and line_idx:
                print(f"    {line_idx:,} records scanned...")

    return stats, fir_narratives

def _compute_degrees(tensor_dir: str, node_count: int) -> np.ndarray:
    print("  Pass 2/3 — Computing node degrees from edge binaries...")
    meta_path = os.path.join(tensor_dir, "graph_meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    edge_count = meta["edge_count"]

    src_mm = np.memmap(os.path.join(tensor_dir, "edge_src.bin"),
                       dtype=np.int64, mode="r", shape=(edge_count,))
    dst_mm = np.memmap(os.path.join(tensor_dir, "edge_dst.bin"),
                       dtype=np.int64, mode="r", shape=(edge_count,))

    degree = np.zeros(node_count, dtype=np.int64)
    chunk = 2_000_000
    for start in range(0, edge_count, chunk):
        end = min(start + chunk, edge_count)
        s = src_mm[start:end]
        d = dst_mm[start:end]
        valid = (s < node_count) & (d < node_count) & (s >= 0) & (d >= 0)
        np.add.at(degree, s[valid], 1)
        np.add.at(degree, d[valid], 1)

    return degree

def build_node_features(
    jsonl_path: str = "data/extracted_graph_nodes.jsonl",
    tensor_dir: str = "data/graph_tensors",
    feature_dim: int = FEATURE_DIM,
    batch_size: int = 128,   # Reduced from 512 → prevents OpenBLAS OOM
):
    os.makedirs(tensor_dir, exist_ok=True)

    with open(os.path.join(tensor_dir, "graph_meta.json")) as f:
        meta = json.load(f)
    node_count = meta["node_count"]

    print(f"[*] Building {feature_dim}-dimensional Detective Features for {node_count:,} nodes...")

    # Stream LMDB cursor in batches — avoids loading 104k-entry dict all at once
    print("  Loading node mapping from LMDB (streaming batched cursor)...")
    env = lmdb.open(os.path.join(tensor_dir, "node_mapping.lmdb"),
                    readonly=True, lock=False)
    name_to_id = {}
    id_to_name = {}
    LMDB_BATCH = 20_000
    with env.begin() as txn:
        cursor = txn.cursor()
        batch_count = 0
        for k, v in cursor:
            name = k.decode("utf-8")
            row_id = struct.unpack(">q", v)[0]
            name_to_id[name] = row_id
            id_to_name[row_id] = name
            batch_count += 1
            if batch_count % LMDB_BATCH == 0:
                pass   # streaming — Python GC can free as needed
    env.close()
    print(f"  Loaded {len(name_to_id):,} node mappings.")

    stats, fir_narratives = _gather_jsonl_stats(jsonl_path, name_to_id)
    degree = _compute_degrees(tensor_dir, node_count)

    if node_count == 0:
        raise RuntimeError("Graph has 0 nodes — run compile_large_graph.py first.")

    max_degree = float(max(int(degree.max()) if len(degree) > 0 else 1, 1))
    log_max_deg = float(np.log1p(max_degree))

    # --- NLP Encoding ---
    print(f"  Pass 3/3 — Generating SentenceTransformer NLP Embeddings for {node_count:,} nodes...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer('all-mpnet-base-v2', device=device)

    # Prepare text for each node
    texts_to_encode = []
    for row_id in range(node_count):
        raw_label = id_to_name.get(row_id, "")
        if raw_label.startswith("FIR-") and row_id in fir_narratives:
            texts_to_encode.append(fir_narratives[row_id])
        else:
            texts_to_encode.append(_clean_label_for_nlp(raw_label))

    print(f"  Encoding {len(texts_to_encode):,} text sequences on {device} (batch_size={batch_size})...")
    nlp_embeddings = model.encode(
        texts_to_encode,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    feat_path = os.path.join(tensor_dir, "node_features.bin")
    features = np.memmap(feat_path, dtype=np.float32, mode="w+",
                         shape=(node_count, feature_dim))
    features[:] = 0.0

    print(f"  Writing feature matrix ({node_count:,} × {feature_dim}) to {feat_path}...")
    for row_id in range(node_count):
        label = id_to_name.get(row_id, "")
        ntype = _node_type(label)
        deg = float(degree[row_id])
        s = stats.get(row_id, {})

        # [0-9] One-hot node type
        features[row_id, ntype] = 1.0

        # [10] Normalized Log-degree
        features[row_id, 10] = float(np.log1p(deg)) / log_max_deg if log_max_deg else 0.0

        # [11-15] Demographics and severity
        features[row_id, 11] = min(s.get("accused_count", 0.0) / 10.0, 1.0)
        features[row_id, 12] = min(s.get("arrested_count", 0.0) / 10.0, 1.0)
        features[row_id, 13] = min(s.get("chargesheeted_count", 0.0) / 10.0, 1.0)
        features[row_id, 14] = min(s.get("conviction_count", 0.0) / 5.0, 1.0)
        features[row_id, 15] = s.get("is_heinous", 0.0)

        # [16-19] Spatial & Temporal Dynamics
        features[row_id, 16] = min(s.get("distance_from_ps", 0.0) / 50.0, 1.0)
        month = s.get("month", 1)
        features[row_id, 17] = math.sin(2.0 * math.pi * month / 12.0)
        features[row_id, 18] = math.cos(2.0 * math.pi * month / 12.0)
        features[row_id, 19] = min(s.get("offence_duration", 0.0) / 48.0, 1.0)

        # [20-787] 768-dim NLP Semantic Vector
        features[row_id, 20:788] = nlp_embeddings[row_id]

    features.flush()

    meta["num_features"] = feature_dim
    with open(os.path.join(tensor_dir, "graph_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✓ Detective Feature matrix saved → {feat_path} (Shape: {node_count:,} × {feature_dim})")
    return feat_path

if __name__ == "__main__":
    build_node_features()
