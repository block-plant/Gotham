"""
Comprehensive Stealth Syndicate Evaluation & Detective Benchmark Suite.
Evaluates model accuracy on standard link prediction AND computes quantitative
Invisible Link Retrieval metrics (Hits@1, Hits@5, Hits@10, MRR) over complex
cross-station syndicates where subgroup leaders have 0 shared arrests.
"""
import os
import sys
import struct
import json
import numpy as np
import torch

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import faiss
import lmdb
from sklearn.metrics import roc_auc_score, average_precision_score

from src.models.dataloader import build_link_loaders
from src.models.model import LinkPredictor
from search import format_node_name, bfs_shortest_path, load_databases, investigate_target

TENSOR_DIR = "data/graph_tensors"
GT_PATH = os.path.join(TENSOR_DIR, "ground_truth_invisible_links.json")
INDEX_PATH = os.path.join(TENSOR_DIR, "node_embeddings.index")
LMDB_PATH = os.path.join(TENSOR_DIR, "node_mapping.lmdb")
REV_LMDB_PATH = os.path.join(TENSOR_DIR, "reverse_mapping.lmdb")
CHECKPOINT_PATH = os.path.join(TENSOR_DIR, "link_predictor.pt")

def evaluate_all():
    print("\n" + "="*85)
    print(" 🕵️‍♂️  STEALTH SYNDICATE ACCURACY & INVISIBLE LINK BENCHMARK  🕵️‍♂️ ".center(85))
    print("="*85)

    if not os.path.exists(INDEX_PATH) or not os.path.exists(CHECKPOINT_PATH):
        print(f"Error: Model or FAISS index not found in {TENSOR_DIR}. Please run training first.")
        return

    # 1. Evaluate Standard Link Prediction on Validation Set
    print("\n[Stage 1/3] Evaluating GNN Link Predictor on Validation Set...")
    data, train_loader, val_loader, labels, meta, loader_mode = build_link_loaders(
        tensor_dir=TENSOR_DIR, batch_size=1024
    )
    
    device = torch.device("cpu")
    ckpt = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=False)
    model = LinkPredictor(
        in_channels=ckpt["in_channels"],
        hidden_channels=ckpt["hidden_channels"],
        num_layers=ckpt["num_layers"],
    ).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    ys, preds = [], []
    with torch.no_grad():
        for batch in val_loader:
            batch = batch.to(device)
            logits = model(batch.x, batch.edge_index, batch.edge_label_index)
            probs = torch.sigmoid(logits).cpu().numpy()
            labels_np = batch.edge_label.cpu().numpy()
            preds.extend(probs.tolist())
            ys.extend(labels_np.tolist())

    roc_auc = float(roc_auc_score(ys, preds)) if len(set(ys)) > 1 else 0.0
    ap = float(average_precision_score(ys, preds)) if len(set(ys)) > 1 else 0.0

    print(f"  ✓ Validation ROC-AUC          : {roc_auc*100:.2f}%")
    print(f"  ✓ Validation Average Precision : {ap*100:.2f}%")

    # 2. Evaluate Invisible Syndicate Retrieval Benchmark (Hits@K, MRR)
    print("\n[Stage 2/3] Evaluating Invisible Syndicate Link Retrieval on Stealth Benchmark...")
    if not os.path.exists(GT_PATH):
        print(f"Warning: {GT_PATH} not found. Skipping invisible benchmark.")
        return

    with open(GT_PATH, "r", encoding="utf-8") as f_gt:
        gt_data = json.load(f_gt)

    syndicates = gt_data.get("syndicates", [])
    print(f"  Loaded {len(syndicates)} stealth syndicates ({gt_data.get('total_injected_records', 0)} cases).")

    index = faiss.read_index(INDEX_PATH)
    env = lmdb.open(LMDB_PATH, readonly=True, lock=False)
    rev_env = lmdb.open(REV_LMDB_PATH, readonly=True, lock=False)

    def get_id(name):
        with env.begin() as txn:
            val = txn.get(name.encode("utf-8"))
        if val is None: return None
        return struct.unpack(">q", val)[0]

    hits_1 = 0
    hits_5 = 0
    hits_10 = 0
    hits_20 = 0
    reciprocal_ranks = []
    total_invisible_queries = 0
    syndicate_scores = []

    for syn in syndicates:
        syn_name = syn["syndicate_name"]
        case_ids = syn["case_ids"]
        syn_node_ids = [get_id(c) for c in case_ids if get_id(c) is not None]
        
        if len(syn_node_ids) < 2:
            continue

        syn_hits_10 = 0
        syn_queries = 0

        # Query each case in the syndicate and check how many of its invisible partners are retrieved
        for query_node_id in syn_node_ids:
            target_partner_ids = set(syn_node_ids) - {query_node_id}
            if not target_partner_ids: continue

            # Fetch vector
            qvec = np.expand_dims(index.reconstruct(query_node_id), axis=0)
            distances, indices = index.search(qvec, 50)

            retrieved_ids = [int(idx) for idx in indices[0] if int(idx) != query_node_id]

            # Calculate metrics
            total_invisible_queries += 1
            syn_queries += 1

            # Check if any partner is in top K
            top_1 = set(retrieved_ids[:1])
            top_5 = set(retrieved_ids[:5])
            top_10 = set(retrieved_ids[:10])
            top_20 = set(retrieved_ids[:20])

            if target_partner_ids & top_1: hits_1 += 1
            if target_partner_ids & top_5: hits_5 += 1
            if target_partner_ids & top_10: 
                hits_10 += 1
                syn_hits_10 += 1
            if target_partner_ids & top_20: hits_20 += 1

            # Reciprocal Rank (rank of first retrieved partner)
            first_rank = 0
            for rank_idx, r_id in enumerate(retrieved_ids, start=1):
                if r_id in target_partner_ids:
                    first_rank = rank_idx
                    break
            if first_rank > 0:
                reciprocal_ranks.append(1.0 / first_rank)
            else:
                reciprocal_ranks.append(0.0)

        syn_acc = (syn_hits_10 / max(1, syn_queries)) * 100
        syndicate_scores.append((syn_name, syn_acc, syn["crime_group"], syn["crime_head"]))

    mrr = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0
    h1_rate = (hits_1 / max(1, total_invisible_queries)) * 100
    h5_rate = (hits_5 / max(1, total_invisible_queries)) * 100
    h10_rate = (hits_10 / max(1, total_invisible_queries)) * 100
    h20_rate = (hits_20 / max(1, total_invisible_queries)) * 100

    print("\n" + "-"*85)
    print(" 📊  QUANTITATIVE INVISIBLE LINK RETRIEVAL PERFORMANCE:")
    print("-" * 85)
    print(f"  • Hits@1  (Top-1 Partner Match)    : {h1_rate:5.1f}%")
    print(f"  • Hits@5  (Top-5 Partner Match)    : {h5_rate:5.1f}%")
    print(f"  • Hits@10 (Top-10 Partner Match)   : {h10_rate:5.1f}%")
    print(f"  • Hits@20 (Top-20 Partner Match)   : {h20_rate:5.1f}%")
    print(f"  • Mean Reciprocal Rank (MRR)       : {mrr:5.3f}")
    print("-" * 85)

    print("\n[Stage 3/3] Syndicate Retrieval Accuracy Breakdown:")
    for syn_name, score, cg, mo in syndicate_scores[:5]:
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        print(f"  [{bar}] {score:5.1f}%  {syn_name} ({cg} -> {mo})")

    env.close()
    rev_env.close()

    # 3. Demonstration of Live Detective Queries on Major Syndicates
    print("\n" + "="*85)
    print(" 🔎  LIVE DETECTIVE QUERY DEMONSTRATION ON INVISIBLE SYNDICATES  🔎 ".center(85))
    print("="*85)

    for s_idx, syn in enumerate(syndicates[:3], start=1):
        target_fir = syn["case_ids"][0]
        print(f"\n[DEMO {s_idx}/3] Querying Syndicate Leader: {syn['syndicate_name']}")
        print(f"       Description: {syn['description']}")
        print(f"       Target Case: {target_fir}")
        investigate_target(query=target_fir, threshold=0.50, limit=5)

    print("="*85)
    print("✓ BENCHMARK & EVALUATION COMPLETE!")
    print("="*85 + "\n")

if __name__ == "__main__":
    evaluate_all()
