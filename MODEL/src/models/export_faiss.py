"""
Export Node Embeddings to a FAISS Vector Database for Fast Real-Time Inference.
"""
import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import numpy as np
try:
    import faiss
except ImportError:
    faiss = None

from src.models.dataloader import build_graph_data
from src.models.model import LinkPredictor
from src.graph_builder.graph_io import resolve_device

def export_to_faiss(
    tensor_dir="data/graph_tensors",
    checkpoint_path="data/graph_tensors/link_predictor.pt",
):
    if faiss is None:
        raise ImportError("Please install faiss-cpu: pip install faiss-cpu")
        
    device = torch.device("cpu")
    print("[*] Loading graph structure and node features...")
    data, meta = build_graph_data(tensor_dir)
    data = data.to(device)
    
    if not os.path.exists(checkpoint_path):
        print(f"Checkpoint not found at {checkpoint_path}. Please train the model first.")
        return None
        
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model = LinkPredictor(
        in_channels=ckpt["in_channels"],
        hidden_channels=ckpt["hidden_channels"],
        num_layers=ckpt["num_layers"],
    ).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    
    print(f"[*] Generating GNN latent embeddings for all {meta['node_count']:,} nodes...")
    with torch.no_grad():
        embeddings = model.encode(data.x, data.edge_index).cpu().numpy()
        embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)

    print(f"  Embeddings shape: {embeddings.shape}")
    
    # Normalize for Cosine Similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings = embeddings / norms
    dim = embeddings.shape[1]
    
    # Build FAISS Index with Inner Product (Cosine Similarity)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    
    out_path = os.path.join(tensor_dir, "node_embeddings.index")
    faiss.write_index(index, out_path)
    
    print(f"✓ FAISS index saved to {out_path} with {index.ntotal:,} vectors.")
    return out_path

if __name__ == "__main__":
    export_to_faiss()
