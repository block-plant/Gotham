"""Shared disk-backed graph I/O utilities."""
import json
import os
import struct

import lmdb
import numpy as np
import torch


def load_graph_meta(tensor_dir="graph_tensors"):
    meta_path = os.path.join(tensor_dir, "graph_meta.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(
            f"{meta_path} not found. Run compile_large_graph.py first."
        )
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def open_node_mapping(tensor_dir="graph_tensors", readonly=True):
    path = os.path.join(tensor_dir, "node_mapping.lmdb")
    return lmdb.open(path, readonly=readonly, lock=readonly)


def open_reverse_mapping(tensor_dir="graph_tensors", readonly=True):
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


def load_edge_index(tensor_dir="graph_tensors", symmetrize=True):
    meta = load_graph_meta(tensor_dir)
    edge_count = meta["edge_count"]
    node_count = meta["node_count"]

    src_path = os.path.join(tensor_dir, "edge_src.bin")
    dst_path = os.path.join(tensor_dir, "edge_dst.bin")
    edge_src = np.memmap(src_path, dtype=np.int64, mode="r", shape=(edge_count,))
    edge_dst = np.memmap(dst_path, dtype=np.int64, mode="r", shape=(edge_count,))

    edge_index = torch.from_numpy(
        np.vstack([edge_src[:], edge_dst[:]]).copy()
    ).long()

    # Filter out any edges that reference node IDs beyond the valid range
    valid_mask = (edge_index[0] < node_count) & (edge_index[1] < node_count)
    edge_index = edge_index[:, valid_mask]

    if symmetrize:
        rev = edge_index.flip(0)
        edge_index = torch.cat([edge_index, rev], dim=1)
        edge_index = torch.unique(edge_index, dim=1)

    return edge_index, meta


def load_node_features(tensor_dir="graph_tensors"):
    meta = load_graph_meta(tensor_dir)
    node_count  = meta["node_count"]
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
