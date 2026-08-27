import sys, torch
sys.path.append('.')
from src.models.investigator import InvestigatorSystem
inv = InvestigatorSystem()

labels = torch.load('data/graph_tensors/link_labels.pt')
pos_edges = labels['val_edge_label_index'][:, labels['val_edge_label'] == 1]

import numpy as np
print("\n--- Highly Correlated FIR Pairs (Big Links) ---")
z_all = inv.model.encode(inv.data.x, inv.data.edge_index)
count = 0
for i in range(1000):
    src, dst = pos_edges[0, i].item(), pos_edges[1, i].item()
    with torch.no_grad():
        struct_feats = inv._compute_struct_feats([src], [dst])
        z_src = z_all[src:src+1]
        z_dst = z_all[dst:dst+1]
        logits = inv.model.decoder(z_src, z_dst, struct_feats)
        prob = torch.sigmoid(logits).item()
        if prob > 0.90:
            name1 = inv.id_to_name.get(src, '')
            name2 = inv.id_to_name.get(dst, '')
            if name1.startswith('FIR') and name2.startswith('FIR'):
                print(f"EVAL_GANG {name1}, {name2}  # Prob: {prob*100:.2f}%")
                count += 1
        if count >= 3:
            break
