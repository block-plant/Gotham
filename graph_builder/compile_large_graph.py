import json
import lmdb
import struct
import os
import numpy as np
import time

def build_scalable_graph(jsonl_path, output_dir="graph_tensors"):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. SETUP LMDB DISK-MAPPER (Zero-RAM String-to-Int Mapping)
    # map_size=10GB allows it to store up to ~100 million unique strings easily
    env = lmdb.open(os.path.join(output_dir, 'node_mapping.lmdb'), map_size=10 * 1024 * 1024 * 1024)
    
    # 2. SETUP MEMORY-MAPPED BINARY ARRAYS
    # We estimate 1 Crore FIRs will produce ~10 Crore edges. 
    # memmap allocates this on the SSD instantly.
    ESTIMATED_MAX_EDGES = 100_000_000 
    
    src_file = os.path.join(output_dir, 'edge_src.bin')
    dst_file = os.path.join(output_dir, 'edge_dst.bin')
    
    edge_src = np.memmap(src_file, dtype=np.int64, mode='w+', shape=(ESTIMATED_MAX_EDGES,))
    edge_dst = np.memmap(dst_file, dtype=np.int64, mode='w+', shape=(ESTIMATED_MAX_EDGES,))
    
    edge_count = 0
    node_count = 0
    
    # Helper function to get/create an ID interacting directly with the SSD
    def get_node_id(txn, entity_str):
        nonlocal node_count
        key = entity_str.encode('utf-8')
        val = txn.get(key)
        if val is not None:
            return struct.unpack('>q', val)[0]
        else:
            new_id = node_count
            txn.put(key, struct.pack('>q', new_id))
            node_count += 1
            return new_id

    # 3. THE STREAMING COMPILER
    print("Beginning high-throughput disk compilation...")
    start_time = time.time()
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        # We use LMDB transactions in batches for maximum disk I/O speed
        txn = env.begin(write=True)
        
        for line_idx, line in enumerate(f):
            record = json.loads(line)
            
            # Map the FIR hub node
            fir_id_str = record.get("fir_id", f"UNKNOWN_FIR_{line_idx}")
            fir_node_id = get_node_id(txn, fir_id_str)
            
            # Phase A: Link all extracted entities to the FIR hub
            entities = record.get("entities", {})
            for cat, items in entities.items():
                for item in items:
                    item_id = get_node_id(txn, item)
                    
                    # Write edge: Entity -> FIR (Undirected, so we write both ways)
                    edge_src[edge_count], edge_dst[edge_count] = item_id, fir_node_id
                    edge_src[edge_count+1], edge_dst[edge_count+1] = fir_node_id, item_id
                    edge_count += 2
            
            # Phase B: Inject the precise NLP Triples (Subject -> Object)
            interactions = record.get("interactions", [])
            for interaction in interactions:
                subj_id = get_node_id(txn, interaction["subject"])
                obj_id = get_node_id(txn, interaction["object"])
                
                # Write directed interaction edge
                edge_src[edge_count], edge_dst[edge_count] = subj_id, obj_id
                edge_count += 1
                
            # Commit the database transaction every 10,000 lines to clear memory
            if line_idx > 0 and line_idx % 10000 == 0:
                txn.commit()
                txn = env.begin(write=True)
                print(f"Processed {line_idx:,} FIRs... (Edges: {edge_count:,})")
                
        # Final commit
        txn.commit()

    # 4. FLUSH AND TRUNCATE
    # Flush the binary arrays to the disk
    edge_src.flush()
    edge_dst.flush()
    
    # We allocated 100M slots, but might have only used 45M. We must note the exact size.
    print(f"\nCompilation Complete in {time.time() - start_time:.2f} seconds!")
    print(f"Total Unique Nodes: {node_count:,}")
    print(f"Total Edges Written: {edge_count:,}")
    print(f"Binary tensors saved to: {output_dir}/")

    meta_path = os.path.join(output_dir, "graph_meta.json")
    with open(meta_path, "w", encoding="utf-8") as meta_f:
        json.dump({"node_count": node_count, "edge_count": edge_count}, meta_f)

    print("Building reverse node index...")
    rev_env = lmdb.open(
        os.path.join(output_dir, "reverse_mapping.lmdb"),
        map_size=10 * 1024 * 1024 * 1024,
    )
    with env.begin() as src_txn, rev_env.begin(write=True) as rev_txn:
        for key, val in src_txn.cursor():
            rev_txn.put(val, key)
    rev_env.close()
    env.close()

if __name__ == "__main__":
    build_scalable_graph("extracted_graph_nodes.jsonl")