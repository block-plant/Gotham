"""
Scalable Disk-Backed Graph Compiler.
Streams extracted entities from extracted_graph_nodes.jsonl into LMDB key-value stores
and memory-mapped binary arrays (edge_src.bin, edge_dst.bin).

Memory fix: reverse_mapping.lmdb map_size reduced from 10 GB → 256 MB.
The actual data for 104k nodes is <15 MB; 256 MB is a safe ceiling.
"""
import json
import lmdb
import struct
import os
import sys
import numpy as np
import time
import argparse

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# 256 MB is vastly sufficient for the reverse mapping (104k nodes × ~50 bytes/entry ≈ 5 MB actual)
_REVERSE_LMDB_MAP_SIZE = 256 * 1024 * 1024   # 256 MB
# Forward mapping: node strings → int IDs. 10 GB is fine here (stores up to ~1M unique strings).
_FORWARD_LMDB_MAP_SIZE = 10 * 1024 * 1024 * 1024   # 10 GB


def build_scalable_graph(jsonl_path="data/extracted_graph_nodes.jsonl", output_dir="data/graph_tensors", max_edges=50_000_000):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Setup LMDB String-to-Int Mapping (forward)
    db_path = os.path.join(output_dir, 'node_mapping.lmdb')
    env = lmdb.open(db_path, map_size=_FORWARD_LMDB_MAP_SIZE)

    # 2. Setup Memory-Mapped Binary Arrays
    src_file = os.path.join(output_dir, 'edge_src.bin')
    dst_file = os.path.join(output_dir, 'edge_dst.bin')

    edge_src = np.memmap(src_file, dtype=np.int64, mode='w+', shape=(max_edges,))
    edge_dst = np.memmap(dst_file, dtype=np.int64, mode='w+', shape=(max_edges,))

    edge_count = 0
    node_count = 0

    def get_node_id(txn, entity_str):
        nonlocal node_count
        key = entity_str.encode('utf-8')[:500]
        val = txn.get(key)
        if val is not None:
            return struct.unpack('>q', val)[0]
        else:
            new_id = node_count
            txn.put(key, struct.pack('>q', new_id))
            node_count += 1
            return new_id

    print(f"[*] Beginning disk graph compilation from {jsonl_path}...")
    start_time = time.time()

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        txn = env.begin(write=True)

        for line_idx, line in enumerate(f):
            try:
                record = json.loads(line)
            except Exception:
                continue

            fir_id_str = record.get("fir_id", f"UNKNOWN_FIR_{line_idx}")
            fir_node_id = get_node_id(txn, fir_id_str)

            # Link all extracted entities to the FIR hub (undirected: 2 edges per entity link)
            entities = record.get("entities", {})
            for cat, items in entities.items():
                for item in items:
                    if edge_count + 2 >= max_edges:
                        print(f"Warning: Reached max_edges capacity ({max_edges:,}). Stopping edge allocation.")
                        break
                    item_id = get_node_id(txn, item)
                    edge_src[edge_count], edge_dst[edge_count] = item_id, fir_node_id
                    edge_src[edge_count+1], edge_dst[edge_count+1] = fir_node_id, item_id
                    edge_count += 2

            # Commit transaction periodically
            if line_idx > 0 and line_idx % 20000 == 0:
                txn.commit()
                txn = env.begin(write=True)
                print(f"  Processed {line_idx:,} FIRs... (Nodes: {node_count:,} | Edges: {edge_count:,})")

        txn.commit()

    # Flush binary arrays
    edge_src.flush()
    edge_dst.flush()

    # Read actual node count from LMDB (handles incremental/restart runs correctly)
    with env.begin() as txn:
        node_count = txn.stat()["entries"]

    print(f"\n✓ Graph Compilation Complete in {time.time() - start_time:.2f}s!")
    print(f"  Total Unique Nodes: {node_count:,}")
    print(f"  Total Edges Written: {edge_count:,}")
    print(f"  Binary tensors saved to: {output_dir}/")

    meta_path = os.path.join(output_dir, "graph_meta.json")
    with open(meta_path, "w", encoding="utf-8") as meta_f:
        json.dump({"node_count": node_count, "edge_count": edge_count}, meta_f, indent=2)

    # Build reverse index with correct (small) map_size
    print(f"Building reverse node index (ID → String) [map_size={_REVERSE_LMDB_MAP_SIZE // (1024*1024)} MB]...")
    rev_db_path = os.path.join(output_dir, "reverse_mapping.lmdb")
    rev_env = lmdb.open(rev_db_path, map_size=_REVERSE_LMDB_MAP_SIZE)

    # Stream cursor in batches to avoid holding all keys in RAM at once
    BATCH = 10_000
    batch_kvs = []
    with env.begin() as src_txn:
        cursor = src_txn.cursor()
        for key, val in cursor:
            batch_kvs.append((val, key))   # reversed: int-bytes → string-bytes
            if len(batch_kvs) >= BATCH:
                with rev_env.begin(write=True) as rev_txn:
                    for k, v in batch_kvs:
                        rev_txn.put(k, v)
                batch_kvs = []

    # Flush remaining
    if batch_kvs:
        with rev_env.begin(write=True) as rev_txn:
            for k, v in batch_kvs:
                rev_txn.put(k, v)

    rev_env.close()
    env.close()
    print("✓ Reverse index ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile disk-backed graph tensors.")
    parser.add_argument("--jsonl", default="data/extracted_graph_nodes.jsonl", help="Input JSONL path")
    parser.add_argument("--output-dir", default="data/graph_tensors", help="Output directory")
    args = parser.parse_args()

    build_scalable_graph(args.jsonl, args.output_dir)