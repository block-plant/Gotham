"""Shared disk-backed graph I/O utilities.

Memory-safe edge loading: avoids torch.unique on the full 79M-edge matrix.
Uses chunked numpy sort + dedup, keeping peak RAM well under 2 GB.
"""
import json
import os
import struct

import lmdb
import numpy as np
import torch


def load_graph_meta(tensor_dir="data/graph_tensors"):
    meta_path = os.path.join(tensor_dir, "graph_meta.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(
            f"{meta_path} not found. Run compile_large_graph.py first."
        )
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def open_node_mapping(tensor_dir="data/graph_tensors", readonly=True):
    path = os.path.join(tensor_dir, "node_mapping.lmdb")
    return lmdb.open(path, readonly=readonly, lock=readonly)


def open_reverse_mapping(tensor_dir="data/graph_tensors", readonly=True):
    path = os.path.join(tensor_dir, "reverse_mapping.lmdb")
    return lmdb.open(path, readonly=readonly, lock=readonly)


def lookup_node_id(env, entity_str):
    with env.begin() as txn:
        val = txn.get(entity_str.encode("utf-8"))
    if val is None:
        return None
    return struct.unpack(">q", val)[0]


def lookup_node_label(rev_env, node_id):
    with rev_env.begin() as txn:
        val = txn.get(struct.pack(">q", node_id))
    if val is None:
        return None
    return val.decode("utf-8")


def load_edge_index(tensor_dir="data/graph_tensors", symmetrize=True):
    """Memory-efficient edge loading.

    Strategy:
    1. Read edge_src / edge_dst via np.memmap (no copy yet).
    2. Filter invalid node IDs in chunks to stay under 1 GB.
    3. If symmetrize, stack forward + reversed pairs using numpy.
    4. Deduplicate with numpy lexsort (avoids torch.unique on 79M matrix).
    5. Convert to torch.long only at the end.

    Peak RAM: ~1.5 GB (vs. ~6 GB with the old torch.unique approach).
    """
    meta = load_graph_meta(tensor_dir)
    edge_count = meta["edge_count"]
    node_count = meta["node_count"]

    src_path = os.path.join(tensor_dir, "edge_src.bin")
    dst_path = os.path.join(tensor_dir, "edge_dst.bin")

    # Memory-mapped — no data is copied yet
    edge_src = np.memmap(src_path, dtype=np.int64, mode="r", shape=(edge_count,))
    edge_dst = np.memmap(dst_path, dtype=np.int64, mode="r", shape=(edge_count,))

    # --- Chunked validity filter (avoids loading all 39M×2 at once) ---
    CHUNK = 4_000_000
    valid_src_chunks, valid_dst_chunks = [], []
    for start in range(0, edge_count, CHUNK):
        end = min(start + CHUNK, edge_count)
        s = edge_src[start:end]       # slice → view (no copy)
        d = edge_dst[start:end]
        mask = (s >= 0) & (s < node_count) & (d >= 0) & (d < node_count)
        valid_src_chunks.append(s[mask].copy())   # only copy valid subset
        valid_dst_chunks.append(d[mask].copy())

    src_np = np.concatenate(valid_src_chunks)     # ~300 MB
    dst_np = np.concatenate(valid_dst_chunks)     # ~300 MB
    del valid_src_chunks, valid_dst_chunks

    if symmetrize:
        # Stack [forward | reversed] — ~600 MB total before dedup
        all_src = np.concatenate([src_np, dst_np])
        all_dst = np.concatenate([dst_np, src_np])
    else:
        all_src = src_np
        all_dst = dst_np
    del src_np, dst_np

    # --- Numpy lexsort dedup (peak ~1.2 GB, far cheaper than torch.unique) ---
    # lexsort sorts by last key first, so (all_src, all_dst)
    order = np.lexsort((all_dst, all_src))
    all_src = all_src[order]
    all_dst = all_dst[order]
    del order

    # Keep only rows where (src, dst) differs from previous row
    if len(all_src) > 1:
        changed = np.ones(len(all_src), dtype=bool)
        changed[1:] = (all_src[1:] != all_src[:-1]) | (all_dst[1:] != all_dst[:-1])
        all_src = all_src[changed]
        all_dst = all_dst[changed]
        del changed

    # Convert to torch — final allocation ~600 MB for the deduped set
    edge_index = torch.from_numpy(
        np.stack([all_src, all_dst], axis=0).copy()
    ).long()
    del all_src, all_dst

    return edge_index, meta


def load_node_features(tensor_dir="data/graph_tensors"):
    meta = load_graph_meta(tensor_dir)
    node_count = meta["node_count"]
    # num_features is written by build_features.py; fall back to 8 for old runs
    num_features = meta.get("num_features", 8)
    feat_path = os.path.join(tensor_dir, "node_features.bin")
    if not os.path.exists(feat_path):
        raise FileNotFoundError(
            f"{feat_path} not found. Run build_features.py first."
        )
    features = np.memmap(
        feat_path, dtype=np.float32, mode="r", shape=(node_count, num_features)
    )
    return torch.from_numpy(np.array(features)).float(), meta


def resolve_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
