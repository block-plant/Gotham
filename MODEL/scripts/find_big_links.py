import torch
import lmdb
import struct
import numpy as np
import sys, os

# Load test edges which we know contain actual positive pairs (syndicates)
print("Loading edges...")
labels = torch.load('data/graph_tensors/link_labels.pt')
test_edges = labels['val_edge_label_index']
test_labels = labels['val_edge_label']

pos_edges = test_edges[:, test_labels == 1]

print("Loading LMDB...")
env = lmdb.open('data/graph_tensors/node_mapping.lmdb', readonly=True)
id_to_name = {}
with env.begin() as txn:
    for k, v in txn.cursor():
        row_id = struct.unpack('>q', v)[0]
        name = k.decode('utf-8')
        if row_id not in id_to_name or name.startswith("FIR"):
            id_to_name[row_id] = name

print("\n--- Highly Correlated FIR Pairs (Big Links) ---")
count = 0
for i in range(pos_edges.size(1)):
    src = pos_edges[0, i].item()
    dst = pos_edges[1, i].item()
    name1 = id_to_name.get(src, '')
    name2 = id_to_name.get(dst, '')
    if name1.startswith('FIR') and name2.startswith('FIR'):
        if name1 != name2:
            print(f"EVAL_GANG {name1}, {name2}")
            count += 1
    if count >= 3:
        break
