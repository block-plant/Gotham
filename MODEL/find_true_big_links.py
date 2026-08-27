import sys, json, torch, os
sys.path.append('.')
import lmdb, struct
import numpy as np
from src.models.investigator import InvestigatorSystem

inv = InvestigatorSystem()

print("Loading val edges...")
labels = torch.load('data/graph_tensors/link_labels.pt')
test_edges = labels['val_edge_label_index']
test_labels = labels['val_edge_label']

pos_edges = test_edges[:, test_labels == 1]

print("\n--- Scanning for TRUE High Confidence Links ---")
count = 0
print("Encoding full graph once (may take ~10GB memory)...")
with torch.no_grad():
    z_all = inv.model.encode(inv.data.x, inv.data.edge_index)

for i in range(5000):
    src = pos_edges[0, i].item()
    dst = pos_edges[1, i].item()
    
    name1 = inv.id_to_name.get(src, '')
    name2 = inv.id_to_name.get(dst, '')
    if not (name1.startswith('FIR') and name2.startswith('FIR')):
        continue
        
    with torch.no_grad():
        struct_feats = inv._compute_struct_feats([src], [dst])
        z_src = z_all[src:src+1]
        z_dst = z_all[dst:dst+1]
        
        logits = inv.model.decoder(z_src, z_dst, struct_feats)
        prob = torch.sigmoid(logits).item()
        
        if prob > 0.8:
            print(f"EVAL_GANG {name1}, {name2}  # Prob: {prob*100:.2f}%")
            count += 1
            if count >= 3:
                break
