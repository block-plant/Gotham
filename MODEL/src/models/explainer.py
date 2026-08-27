"""Graph Connection Explainer using PyTorch Geometric."""
import torch
from torch_geometric.explain import Explainer, GNNExplainer

def get_explainer(model):
    """
    Initializes a GNNExplainer for the LinkPredictor model.
    """
    explainer = Explainer(
        model=model,
        algorithm=GNNExplainer(epochs=200),
        explanation_type='model',
        edge_mask_type='object',
        model_config=dict(
            mode='binary_classification',
            task_level='edge',
            return_type='raw',
        ),
    )
    return explainer


def explain_connection(explainer, data, src_node, dst_node, node_mapping_env=None):
    """
    Explains why a connection exists between src_node and dst_node.
    Returns a list of important edges (reasons) contributing to the prediction.
    """
    edge_label_index = torch.tensor([[src_node], [dst_node]], dtype=torch.long, device=data.x.device)
    
    explanation = explainer(
        data.x, 
        data.edge_index, 
        edge_label_index=edge_label_index
    )
    
    edge_mask = explanation.edge_mask
    if edge_mask is None:
        return []

    # Get the top 10 most important edges contributing to this connection
    top_k = min(10, edge_mask.size(0))
    top_edges = edge_mask.argsort(descending=True)[:top_k]
    
    reasons = []
    for idx in top_edges:
        src = data.edge_index[0, idx].item()
        dst = data.edge_index[1, idx].item()
        importance = edge_mask[idx].item()
        
        # If importance is very low, skip
        if importance < 0.1:
            continue
            
        reasons.append({
            "src_id": src,
            "dst_id": dst,
            "importance": round(importance, 4)
        })
        
    return reasons
