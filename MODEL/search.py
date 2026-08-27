"""
Detective-Grade Criminal Linkage & Syndicate Intelligence Engine.
Usage:
    # 1. Query an existing Case ID (JSON output)
    python search.py --fir_id "FIR-1898733" --json

    # 2. Query using specific fields from frontend
    python search.py --crime_type "ROBBERY" --modus_operandi "CHAIN_SNATCHING" --location "Bus Stand" --json

    # 3. Interactive Detective Console
    python search.py --interactive
"""
import os
import sys
import struct
import argparse
import json
import re
import math
from collections import defaultdict, deque

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import faiss
import numpy as np
import lmdb
import torch
from sentence_transformers import SentenceTransformer

from src.data_processing.hybrid_extractor import (
    normalize_act_sections,
    extract_landmarks,
    parse_distance_km,
    clean_string,
    LANDMARK_PATTERNS
)
from src.graph_builder.graph_io import lookup_node_id, lookup_node_label
from src.models.model import LinkPredictor

TENSOR_DIR = "data/graph_tensors"
INDEX_PATH = os.path.join(TENSOR_DIR, "node_embeddings.index")
LMDB_PATH = os.path.join(TENSOR_DIR, "node_mapping.lmdb")
REV_LMDB_PATH = os.path.join(TENSOR_DIR, "reverse_mapping.lmdb")
CHECKPOINT_PATH = os.path.join(TENSOR_DIR, "link_predictor.pt")

FEATURE_DIM = 788

# Lazy-loaded globals
_SENTENCE_MODEL = None
_GNN_MODEL = None
_FAISS_INDEX = None
_LMDB_ENV = None
_REV_LMDB_ENV = None
_ADJ_LIST = None
_NODE_META = None

def get_sentence_model():
    global _SENTENCE_MODEL
    if _SENTENCE_MODEL is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _SENTENCE_MODEL = SentenceTransformer('all-mpnet-base-v2', device=device)
    return _SENTENCE_MODEL

def get_gnn_model():
    global _GNN_MODEL
    if _GNN_MODEL is None and os.path.exists(CHECKPOINT_PATH):
        try:
            ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
            model = LinkPredictor(
                in_channels=ckpt["in_channels"],
                hidden_channels=ckpt["hidden_channels"],
                num_layers=ckpt["num_layers"],
            )
            model.load_state_dict(ckpt["model_state"])
            model.eval()
            _GNN_MODEL = model
        except Exception as e:
            pass
    return _GNN_MODEL

def load_databases():
    global _FAISS_INDEX, _LMDB_ENV, _REV_LMDB_ENV, _ADJ_LIST, _NODE_META

    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(f"FAISS index not found at {INDEX_PATH}.")
    
    if _FAISS_INDEX is None:
        _FAISS_INDEX = faiss.read_index(INDEX_PATH)
    if _LMDB_ENV is None:
        _LMDB_ENV = lmdb.open(LMDB_PATH, readonly=True, lock=False)
    if _REV_LMDB_ENV is None:
        _REV_LMDB_ENV = lmdb.open(REV_LMDB_PATH, readonly=True, lock=False)

    if _NODE_META is None:
        meta_path = os.path.join(TENSOR_DIR, "graph_meta.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            _NODE_META = json.load(f)

    if _ADJ_LIST is None:
        _ADJ_LIST = defaultdict(list)
        try:
            edge_count = _NODE_META["edge_count"]
            src_mm = np.memmap(os.path.join(TENSOR_DIR, "edge_src.bin"), dtype=np.int64, mode="r", shape=(edge_count,))
            dst_mm = np.memmap(os.path.join(TENSOR_DIR, "edge_dst.bin"), dtype=np.int64, mode="r", shape=(edge_count,))
            max_edges = min(edge_count, 10_000_000)
            for s, d in zip(src_mm[:max_edges], dst_mm[:max_edges]):
                _ADJ_LIST[int(s)].append(int(d))
        except Exception:
            pass

def format_node_name(name):
    if not name: return "Unknown"
    if name.startswith("FIR-"): return f"CASE: {name}"
    if name.startswith("MO_"): return f"MODUS: {name[3:].replace('_', ' ')}"
    if name.startswith("CG_"): return f"CATEGORY: {name[3:].replace('_', ' ')}"
    if name.startswith("ACT_"): return f"STATUTE: {name[4:].replace('_', ' ')}"
    if name.startswith("BEAT_"): return f"BEAT: {name[5:].replace('_', ' ')}"
    if name.startswith("UNIT_"): return f"STATION: {name[5:].replace('_', ' ')}"
    if name.startswith("DIST_"): return f"DISTRICT: {name[5:].replace('_', ' ')}"
    if name.startswith("AREA_"): return f"AREA: {name[5:].replace('_', ' ')}"
    if name.startswith("IO_"): return f"OFFICER: {name[3:].replace('_', ' ')}"
    if name.startswith("LANDMARK_"): return f"LANDMARK: {name[9:].replace('_', ' ')}"
    if name.startswith("GANG_"): return f"GANG: {name[5:].replace('_', ' ')}"
    return name

def bfs_shortest_path(adj, start_id, target_id, max_depth=4):
    if not adj or start_id not in adj: return None
    queue = deque([(start_id, [start_id])])
    visited = {start_id}
    while queue:
        curr, path = queue.popleft()
        if len(path) > max_depth + 1: break
        for neighbor in adj.get(curr, []):
            if neighbor == target_id:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None

def extract_clues_from_fields(text: str, crime_type: str, mo: str, location: str, statutes: str, accused: int) -> dict:
    text_upper = (text or "").upper()
    
    detected_cg = crime_type or "GENERAL"
    detected_mo = mo or "UNKNOWN"
    acts = statutes.split(",") if statutes else []
    landmarks = [location] if location else []
    
    if not crime_type and text:
        if "SNATCH" in text_upper: detected_cg = "ROBBERY"; detected_mo = "CHAIN_SNATCHING"
        elif "BURGLARY" in text_upper: detected_cg = "BURGLARY"; detected_mo = "NIGHT_BURGLARY"
        elif "CYBER" in text_upper: detected_cg = "CYBER_CRIME"; detected_mo = "IT_ACT"

    return {
        "crime_group": detected_cg,
        "crime_head": detected_mo,
        "act_sections": acts,
        "landmarks": landmarks,
        "accused_count": accused or 1,
        "raw_text": text or ""
    }

def encode_query_vector(clues: dict) -> np.ndarray:
    model = get_sentence_model()
    narrative = (
        f"[CRIME: {clues['crime_group']}] [MO: {clues['crime_head']}] "
        f"[STATUTES: {', '.join(clues['act_sections'])}] "
        f"[INVESTIGATION CLUE: {clues['raw_text']}] "
        f"[DEMOGRAPHICS: Accused: {clues['accused_count']}]"
    )
    nlp_vec = model.encode([narrative], normalize_embeddings=True)[0]
    feat = np.zeros((1, FEATURE_DIM), dtype=np.float32)
    feat[0, 0] = 1.0
    feat[0, 10] = 0.5
    feat[0, 11] = min(clues["accused_count"] / 10.0, 1.0)
    feat[0, 15] = 1.0 if clues["accused_count"] >= 3 else 0.0
    feat[0, 16] = 0.1
    feat[0, 18] = 1.0
    feat[0, 20:788] = nlp_vec
    
    gnn_model = get_gnn_model()
    if gnn_model is not None:
        with torch.no_grad():
            x_t = torch.from_numpy(feat).float()
            self_loop = torch.tensor([[0], [0]], dtype=torch.long)
            z = gnn_model.encode(x_t, self_loop).cpu().numpy()[0]
            norm = np.linalg.norm(z)
            if norm > 0: z = z / norm
            return z
    return nlp_vec[:128]

def search_by_vector(query_vec: np.ndarray, k: int = 15, threshold: float = 0.55):
    load_databases()
    q = np.expand_dims(query_vec.astype(np.float32), axis=0)
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    distances, indices = _FAISS_INDEX.search(q, k * 3)
    
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or dist < threshold: continue
        label = lookup_node_label(_REV_LMDB_ENV, int(idx))
        if not label: continue
        results.append({
            "node_id": int(idx),
            "label": label,
            "confidence": float(dist),
        })
        if len(results) >= k: break
    return results

def api_investigate(fir_id=None, text=None, crime_type=None, mo=None, location=None, statutes=None, accused_count=1, threshold=0.50, limit=10, is_json=False):
    """Main API entry point. Returns dictionary list."""
    load_databases()
    
    query_id = None
    results = []
    
    if fir_id:
        clean_q = fir_id.strip()
        if not clean_q.startswith("FIR-") and clean_q.isdigit(): clean_q = f"FIR-{clean_q}"
        query_id = lookup_node_id(_LMDB_ENV, clean_q)
        if query_id is None: query_id = lookup_node_id(_LMDB_ENV, clean_q.upper())
        
        if query_id is not None:
            qvec = _FAISS_INDEX.reconstruct(query_id)
            results = search_by_vector(qvec, k=limit + 1, threshold=threshold)
            results = [r for r in results if r["node_id"] != query_id][:limit]
    else:
        clues = extract_clues_from_fields(text, crime_type, mo, location, statutes, accused_count)
        qvec = encode_query_vector(clues)
        results = search_by_vector(qvec, k=limit, threshold=threshold)
        
    output_data = []
    for r in results:
        node_id = r["node_id"]
        label = r["label"]
        score = r["confidence"]
        
        path_str = ""
        path_nodes = []
        if query_id is not None:
            path = bfs_shortest_path(_ADJ_LIST, query_id, node_id, max_depth=5)
            if path:
                path_labels = [lookup_node_label(_REV_LMDB_ENV, n) or "Unknown" for n in path]
                path_nodes = path_labels
                path_str = " -> ".join([format_node_name(p) for p in path_labels])
                
        output_data.append({
            "target": label,
            "formatted_name": format_node_name(label),
            "confidence": score,
            "path": path_nodes,
            "path_description": path_str
        })
        
    if is_json:
        print(json.dumps({"status": "success", "results": output_data}, indent=2))
        return
        
    if not output_data:
        print(f"No strong linkages found above {threshold*100}% confidence.")
        return
        
    print("\n" + "="*85)
    print(" 🚨 DETECTIVE INTELLIGENCE RESULTS 🚨 ".center(85))
    print("="*85)
    for i, res in enumerate(output_data, 1):
        bar_len = int(res["confidence"] * 10)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        print(f"\n #{i:<2} [{bar}] {res['confidence']*100:5.1f}%  {res['formatted_name']}")
        if res["path_description"]:
            print(f"      └── Trace: {res['path_description']}")
    print("\n" + "="*85)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detective API Search")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--fir_id", type=str, help="Search by exact Case ID")
    parser.add_argument("--text", type=str, help="Free-form clue text")
    parser.add_argument("--crime_type", type=str, help="Crime category (e.g. THEFT)")
    parser.add_argument("--modus_operandi", type=str, help="Specific MO")
    parser.add_argument("--statutes", type=str, help="Comma separated acts")
    parser.add_argument("--location", type=str, help="Landmark or place")
    parser.add_argument("--accused_count", type=int, default=1, help="Number of accused")
    parser.add_argument("--threshold", type=float, default=0.50, help="Confidence threshold")
    parser.add_argument("--limit", type=int, default=10, help="Max results")
    parser.add_argument("--interactive", action="store_true", help="Interactive terminal")
    
    args = parser.parse_args()
    
    if args.interactive:
        print("Interactive mode (Type ID or clue, 'exit' to quit):")
        while True:
            try:
                q = input("> ")
                if q in ['exit', 'quit']: break
                if q.startswith("FIR-") or q.isdigit():
                    api_investigate(fir_id=q, is_json=False)
                else:
                    api_investigate(text=q, is_json=False)
            except (KeyboardInterrupt, EOFError):
                break
    else:
        api_investigate(
            fir_id=args.fir_id,
            text=args.text,
            crime_type=args.crime_type,
            mo=args.modus_operandi,
            location=args.location,
            statutes=args.statutes,
            accused_count=args.accused_count,
            threshold=args.threshold,
            limit=args.limit,
            is_json=args.json
        )
