import os
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"
"""Export Node Embeddings to a FAISS Vector Database for Fast Inference."""
import os
import torch
import numpy as np
try:
    import faiss
except ImportError:
    faiss = None

from models.dataloader import build_graph_data
from models.model import LinkPredictor
from graph_builder.graph_io import resolve_device

def export_to_faiss(
    tensor_dir="graph_tensors",
    checkpoint_path="graph_tensors/link_predictor.pt",
):
    if faiss is None:
        raise ImportError("Please install faiss-cpu or faiss-gpu: pip install faiss-cpu")
        
    device = torch.device("cpu")
    data, meta = build_graph_data(tensor_dir)
    data = data.to(device)
    
    if not os.path.exists(checkpoint_path):
        print("Checkpoint not found. Please train the model first.")
        return
        
    # Load model
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model = LinkPredictor(
        in_channels=ckpt["in_channels"],
        hidden_channels=ckpt["hidden_channels"],
        num_layers=ckpt["num_layers"],
    ).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    
    print("Generating embeddings for all nodes...")
    # For a massive graph, we can't do this in one forward pass. 
    # But for a medium graph (<= 1M nodes), GNNs can do a full-batch forward.
    # We will use PyG's NeighborLoader in inference mode or full batch if it fits in memory.
    
    with torch.no_grad():
        try:
            # Generate the latent Z embeddings
            embeddings = np.ascontiguousarray(model.encode(data.x, data.edge_index).cpu().numpy(), dtype=np.float32)
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                print("OOM: For massive 1Cr+ graphs, use PyG NodeLoader for batched inference.")
                raise e
            else:
                raise e

    print(f"Generated embeddings shape: {embeddings.shape}")
    
    # Build FAISS Index
    # We use L2 normalization + Inner Product for Cosine Similarity (which matches our dot-product decoder)
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    dim = embeddings.shape[1]
    
    # For 1 Crore+ nodes, use IVF (Inverted File Index) or HNSW for speed
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    
    out_path = os.path.join(tensor_dir, "node_embeddings.index")
    faiss.write_index(index, out_path)
    
    print(f"FAISS index saved to {out_path} with {index.ntotal} vectors.")
    return out_path

def search_connections(query_node_id, index_path="graph_tensors/node_embeddings.index", k=10, threshold=0.7):
    """
    Search for connections instantly using FAISS without touching the graph DB.
    """
    if faiss is None:
        raise ImportError("Please install faiss-cpu or faiss-gpu: pip install faiss-cpu")
        
    index = faiss.read_index(index_path)
    
    # We need the query vector. In a real system, we'd either look it up from FAISS 
    # using reconstruct() or fetch it from a key-value store.
    query_vector = np.expand_dims(index.reconstruct(query_node_id), axis=0)
    
    # Search
    distances, indices = index.search(query_vector, k)
    
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if dist >= threshold and idx != query_node_id:
            results.append({"node_id": int(idx), "probability": float(dist)})
            
    return results

if __name__ == "__main__":
    export_to_faiss()
