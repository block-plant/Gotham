import sys, json, torch, os
sys.path.append('.')
import lmdb, struct
import numpy as np
from src.models.investigator import InvestigatorSystem

inv = InvestigatorSystem()

print("ACT_KP_196 ID:", inv.name_to_id.get("ACT_KP_196"))
print("MO_GAMBLING - MATKA (78 CLASS C) ID:", inv.name_to_id.get("MO_GAMBLING - MATKA (78 CLASS C)"))
print("DIST_BAGALKOT ID:", inv.name_to_id.get("DIST_BAGALKOT"))
print("BEAT_AMINAGAD TOWN BEAT NO 1 ID:", inv.name_to_id.get("BEAT_AMINAGAD TOWN BEAT NO 1"))

print("FIR_17 ID:", inv.name_to_id.get("FIR_17"))

fir1_id = inv.name_to_id['FIR_6']
fir2_id = inv.name_to_id['FIR_7']

print(f"FIR 1 ID: {fir1_id}")
print(f"FIR 2 ID: {fir2_id}")

print("FIR 1 JSONL data:", inv.fir_data.get(fir1_id))
print("FIR 2 JSONL data:", inv.fir_data.get(fir2_id))

feats = inv._compute_struct_feats([fir1_id], [fir2_id])
print("Investigator Feats:", feats.tolist())

# Now check what train.py does exactly.
def train_py_exact():
    q_src = [fir1_id]
    q_dst = [fir2_id]
    n = 1
    same_mo = np.zeros(n, dtype=np.float32)
    same_beat = np.zeros(n, dtype=np.float32)
    same_dist = np.zeros(n, dtype=np.float32)
    acts_jac = np.zeros(n, dtype=np.float32)
    
    for i in range(n):
        du = inv.fir_data.get(int(q_src[i]), {})
        dv = inv.fir_data.get(int(q_dst[i]), {})
        if du.get("mo", -1) >= 0 and du["mo"] == dv.get("mo", -2): same_mo[i] = 1.0
        if du.get("beat", -1) >= 0 and du["beat"] == dv.get("beat", -2): same_beat[i] = 1.0
        if du.get("district", -1) >= 0 and du["district"] == dv.get("district", -2): same_dist[i] = 1.0
        au = du.get("acts", frozenset())
        av = dv.get("acts", frozenset())
        if au or av:
            inter = len(au & av)
            union = len(au | av)
            acts_jac[i] = inter / union if union > 0 else 0.0
            
    return np.stack([same_mo, same_beat, same_dist, acts_jac], axis=1)

print("Train.py Feats:", train_py_exact().tolist())
