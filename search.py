"""
Criminal Connection Investigator
Usage:
    python search.py --query "Aachal Aggarwal" --threshold 0.70
    python search.py --query "6016912892" --threshold 0.50 --limit 20
"""
import os
import struct
import argparse

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import faiss
import numpy as np
import lmdb


TENSOR_DIR = "graph_tensors"
INDEX_PATH  = os.path.join(TENSOR_DIR, "node_embeddings.index")
LMDB_PATH   = os.path.join(TENSOR_DIR, "node_mapping.lmdb")


def load_maps():
    """Load LMDB into two dicts: name→row_id  and  row_id→name."""
    if not os.path.exists(LMDB_PATH):
        raise FileNotFoundError(f"Database not found at {LMDB_PATH}. Did you run the pipeline?")

    name_to_id = {}
    id_to_name = {}
    env = lmdb.open(LMDB_PATH, readonly=True, lock=False)
    with env.begin() as txn:
        cursor = txn.cursor()
        for key_bytes, val_bytes in cursor:
            name   = key_bytes.decode("utf-8")
            row_id = struct.unpack(">q", val_bytes)[0]   # big-endian int64
            name_to_id[name]   = row_id
            id_to_name[row_id] = name
    env.close()
    return name_to_id, id_to_name


def search_connections(query_name: str, threshold: float = 0.65,
                       k: int = 15, tensor_dir: str = TENSOR_DIR):
    print(f"\nInvestigating: {query_name!r}")
    print(f"Threshold: {threshold*100:.0f}%  |  Max results: {k}\n")

    # ── 1. Load maps ────────────────────────────────────────────────────────
    print("Loading node database...")
    name_to_id, id_to_name = load_maps()

    if query_name not in name_to_id:
        print(f"  ERROR: '{query_name}' not found in police records.")
        print("  Tip: Use the exact name as it appears in the FIR narratives.")
        print("  Example names from the dataset:")
        print("    Aachal Aggarwal, Oviya Dhingra, Aachal Arora")
        print("  Example phones: 6016912892, 6027102707")
        return

    row_id = name_to_id[query_name]
    print(f"  Target found. Internal row ID: {row_id}")

    # ── 2. Load FAISS ────────────────────────────────────────────────────────
    if not os.path.exists(INDEX_PATH):
        print(f"  ERROR: FAISS index not found at {INDEX_PATH}.")
        print("  Run:  python -m models.export_faiss")
        return

    index = faiss.read_index(INDEX_PATH)
    print(f"  FAISS index loaded. {index.ntotal:,} vectors (dimension={index.d})\n")

    # ── 3. Reconstruct query vector and search ───────────────────────────────
    try:
        qvec = np.expand_dims(index.reconstruct(row_id), axis=0)
    except Exception as e:
        print(f"  ERROR: Could not retrieve embedding for row {row_id}: {e}")
        return

    distances, indices = index.search(qvec, k + 1)   # +1 to account for self

    # ── 4. Filter and display results ────────────────────────────────────────
    print(f"{'Rank':<5}  {'Probability':>12}  {'Connection'}")
    print("-" * 60)

    rank = 0
    found_any = False
    for dist, idx in zip(distances[0], indices[0]):
        if int(idx) == row_id:
            continue                    # skip self
        if dist < threshold:
            continue                    # below confidence threshold

        connected_name = id_to_name.get(int(idx), f"Unknown-Node-{idx}")
        rank += 1
        bar_len = int(dist * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"  {rank:<3}  [{bar}]  {dist*100:5.1f}%   {connected_name}")
        found_any = True

    if not found_any:
        print(f"  No connections found above {threshold*100:.0f}% threshold.")
        print(f"  Try lowering --threshold to 0.30 to see weak connections.")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Investigator — find criminal connections using the trained GNN model."
    )
    parser.add_argument(
        "--query", type=str, required=True,
        help="Exact name, phone number, or vehicle number to investigate."
    )
    parser.add_argument(
        "--threshold", type=float, default=0.65,
        help="Minimum confidence threshold (0.0–1.0). Default: 0.65"
    )
    parser.add_argument(
        "--limit", type=int, default=15,
        help="Maximum number of connections to return. Default: 15"
    )
    args = parser.parse_args()
    search_connections(args.query, threshold=args.threshold, k=args.limit)
