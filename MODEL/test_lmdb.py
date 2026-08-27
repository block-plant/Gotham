import lmdb, struct
env = lmdb.open('data/graph_tensors/node_mapping.lmdb', readonly=True)
txn = env.begin()
items = [(k.decode(), struct.unpack('>q', v)[0]) for i, (k, v) in enumerate(txn.cursor()) if i < 30]
for k, v in items:
    print(f"{k}: {v}")

print("ACT_KP_196:", struct.unpack('>q', txn.get(b'ACT_KP_196'))[0] if txn.get(b'ACT_KP_196') else None)
print("FIR_17:", struct.unpack('>q', txn.get(b'FIR_17'))[0] if txn.get(b'FIR_17') else None)
print("FIR_6:", struct.unpack('>q', txn.get(b'FIR_6'))[0] if txn.get(b'FIR_6') else None)
print("FIR_0:", struct.unpack('>q', txn.get(b'FIR_0'))[0] if txn.get(b'FIR_0') else None)
print("DIST_BAGALKOT:", struct.unpack('>q', txn.get(b'DIST_BAGALKOT'))[0] if txn.get(b'DIST_BAGALKOT') else None)
