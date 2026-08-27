"""
Production Investigator Inference Script
Provides real-time Inductive Link Prediction for new FIRs, and Entity Interrogation.
"""
import os
import sys
import json
import torch
import numpy as np
import lmdb
import struct
import argparse
import time

try:
    import faiss
except ImportError:
    faiss = None

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.models.model import LinkPredictor
from src.models.dataloader import build_graph_data

def get_node_type(label: str) -> int:
    if not label: return 9
    if label.startswith("FIR-") or label.startswith("FIR_"): return 0
    if label.startswith("MO_"): return 1
    if label.startswith("CG_"): return 2
    if label.startswith("ACT_"): return 3
    if label.startswith("BEAT_"): return 4
    if label.startswith("UNIT_"): return 5
    if label.startswith("DIST_"): return 6
    if label.startswith("AREA_"): return 7
    if label.startswith("IO_"): return 8
    if label.startswith("LANDMARK_") or label.startswith("GANG_"): return 9
    return 9

class InvestigatorSystem:
    def __init__(self, tensor_dir="data/graph_tensors", device="cpu"):
        self.tensor_dir = tensor_dir
        self.device = torch.device(device)
        
        print("[*] Booting Investigator System...")
        
        if faiss is None:
            raise ImportError("Please install faiss-cpu: pip install faiss-cpu")
            
        index_path = os.path.join(tensor_dir, "node_embeddings.index")
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"FAISS index not found at {index_path}. Please run export_faiss.py first.")
        
        print("  Loading FAISS Vector Database...")
        self.index = faiss.read_index(index_path)
        
        print("  Loading Graph Structure and Mappings...")
        self.data, self.meta = build_graph_data(tensor_dir)
        self.data = self.data.to(self.device)
        
        # Load LMDB Mapping
        cache_mapping = os.path.join(tensor_dir, "mapping_cache.pkl")
        if os.path.exists(cache_mapping):
            import pickle
            with open(cache_mapping, "rb") as f:
                self.name_to_id, self.id_to_name = pickle.load(f)
        else:
            self.env = lmdb.open(os.path.join(tensor_dir, "node_mapping.lmdb"), readonly=True, lock=False)
            self.name_to_id = {}
            self.id_to_name = {}
            with self.env.begin() as txn:
                for k, v in txn.cursor():
                    name = k.decode('utf-8')
                    row_id = struct.unpack('>q', v)[0]
                    self.name_to_id[name] = row_id
                    if row_id not in self.id_to_name or name.startswith("FIR"):
                        self.id_to_name[row_id] = name
            import pickle
            with open(cache_mapping, "wb") as f:
                pickle.dump((self.name_to_id, self.id_to_name), f, protocol=pickle.HIGHEST_PROTOCOL)
                
        # Load Model
        ckpt_path = os.path.join(tensor_dir, "link_predictor.pt")
        ckpt = torch.load(ckpt_path, map_location=self.device, weights_only=False)
        self.model = LinkPredictor(
            in_channels=ckpt["in_channels"],
            hidden_channels=ckpt["hidden_channels"],
            num_layers=ckpt["num_layers"],
        ).to(self.device)
        self.model.load_state_dict(ckpt["model_state"])
        self.model.eval()
        
        print("  Building Sparse Adjacency Matrices for exact matching...")
        import scipy.sparse as sp
        src_np = self.data.edge_index[0].cpu().numpy()
        dst_np = self.data.edge_index[1].cpu().numpy()
        N = self.data.num_nodes
        self.adj = sp.csr_matrix((np.ones(len(src_np), dtype=np.float32), (src_np, dst_np)), shape=(N, N))
        
        self.node_types = self.data.x[:, :10].argmax(dim=-1).cpu().numpy()
        self.typed_adjs = {}
        
        TYPE_MAP = [
            ("MO", 1), ("CG", 2), ("ACT", 3), 
            ("BEAT", 6), ("AREA", 7), ("IO", 8)
        ]
        
        for t_name, t_idx in TYPE_MAP:
            mask = self.node_types[dst_np] == t_idx
            self.typed_adjs[t_name] = sp.csr_matrix(
                (np.ones(mask.sum(), dtype=np.float32), 
                (src_np[mask], dst_np[mask])), 
                shape=(N, N)
            )
            
        print("  Loading Exact Match Features...")
        cache_path = os.path.join(tensor_dir, "fir_data_cache.pkl")
        if os.path.exists(cache_path):
            import pickle
            with open(cache_path, "rb") as f:
                self.fir_data = pickle.load(f)
        else:
            import json
            self.fir_data = {}
            jsonl_path = "data/extracted_graph_nodes.jsonl"
            if not os.path.exists(jsonl_path):
                jsonl_path = "../data/extracted_graph_nodes.jsonl"
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    record = json.loads(line)
                    fir_id_str = record.get("fir_id", f"UNKNOWN_FIR_{i}")
                    if fir_id_str in self.name_to_id:
                        u = self.name_to_id[fir_id_str]
                        self.fir_data[u] = {}
                        ent = record.get("entities", {})
                        
                        mos = ent.get("crime_heads", [])
                        if mos: self.fir_data[u]["mo"] = self.name_to_id.get(mos[0], -1)
                        
                        beats = ent.get("beats", [])
                        if beats: self.fir_data[u]["beat"] = self.name_to_id.get(beats[0], -1)
                        
                        districts = ent.get("districts", [])
                        if districts: self.fir_data[u]["district"] = self.name_to_id.get(districts[0], -1)
                        
                        acts = ent.get("act_sections", [])
                        if acts:
                            act_ids = [self.name_to_id[a] for a in acts if a in self.name_to_id]
                            self.fir_data[u]["acts"] = frozenset(act_ids)
            import pickle
            with open(cache_path, "wb") as f:
                pickle.dump(self.fir_data, f, protocol=pickle.HIGHEST_PROTOCOL)
                
        print("✓ System Ready.\n")
        
    def _compute_struct_feats(self, q_src_nodes, q_dst_nodes):
        """
        Compute EXACT MATCH features and CN counts identically to training setup.
        Returns: [batch, 10]
        """
        n = len(q_src_nodes)
        same_mo = np.zeros(n, dtype=np.float32)
        same_beat = np.zeros(n, dtype=np.float32)
        same_dist = np.zeros(n, dtype=np.float32)
        acts_jac = np.zeros(n, dtype=np.float32)
        
        for i in range(n):
            u = q_src_nodes[i]
            v = q_dst_nodes[i]
            du = self.fir_data.get(u, {})
            dv = self.fir_data.get(v, {})
            
            if du.get("mo", -1) >= 0 and du["mo"] == dv.get("mo", -2):
                same_mo[i] = 1.0
            if du.get("beat", -1) >= 0 and du["beat"] == dv.get("beat", -2):
                same_beat[i] = 1.0
            if du.get("district", -1) >= 0 and du["district"] == dv.get("district", -2):
                same_dist[i] = 1.0
                
            au = du.get("acts", frozenset())
            av = dv.get("acts", frozenset())
            if au or av:
                inter = len(au & av)
                union = len(au | av)
                acts_jac[i] = inter / union if union > 0 else 0.0
                
        entity_feats = np.stack([same_mo, same_beat, same_dist, acts_jac], axis=1)
        
        # CN Struct Features
        cn_feats = []
        train_vmax = {
            "MO": 52.0,
            "CG": 1.0,
            "ACT": 1.0,
            "BEAT": 1.0,
            "AREA": 1.0,
            "IO": 5111.0
        }
        
        for t_name in ["MO", "CG", "ACT", "BEAT", "AREA", "IO"]:
            adj = self.typed_adjs[t_name]
            src_n = adj[q_src_nodes, :]
            dst_n = adj[q_dst_nodes, :]
            cn = np.array(src_n.multiply(dst_n).sum(axis=1)).flatten()
            
            # Apply exact log1p scaling used during training
            vmax = train_vmax[t_name]
            cn_scaled = np.log1p(cn) / np.log1p(vmax + 1)
            cn_feats.append(cn_scaled)
            
        cn_feats = np.stack(cn_feats, axis=1)
        return torch.tensor(np.hstack([cn_feats, entity_feats]), dtype=torch.float32).to(self.device)

    def query_entity(self, entity_name: str, top_k=20):
        """Interrogate the graph for an existing entity (Person, Location, Gang, etc.)"""
        print(f"\n[Interrogation] Entity: {entity_name}")
        if entity_name not in self.name_to_id:
            print("  ❌ Entity not found in database.")
            return
            
        node_id = self.name_to_id[entity_name]
        
        if self.node_types[node_id] == 0:
            # It's an FIR. Search FAISS directly.
            with torch.no_grad():
                emb = self.model.encode(self.data.x, self.data.edge_index)[node_id:node_id+1].cpu().numpy()
            norms = np.linalg.norm(emb, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            emb = emb / norms
            distances, indices = self.index.search(emb, top_k * 5)
            
            candidates = []
            for dist, idx in zip(distances[0], indices[0]):
                if self.node_types[idx] == 0:
                    candidates.append(idx)
                if len(candidates) == top_k:
                    break
        else:
            # It's an IO, MO, BEAT, etc.
            # Find its direct FIR neighbors in the graph
            neighbors = self.adj.indices[self.adj.indptr[node_id]:self.adj.indptr[node_id+1]]
            fir_neighbors = [n for n in neighbors if self.node_types[n] == 0]
            
            if not fir_neighbors:
                print("  ❌ This entity is not connected to any known crimes.")
                return
                
            print(f"  ✓ Entity is connected to {len(fir_neighbors)} known crimes. Expanding search...")
            
            # Use its first FIR neighbor as the structural anchor to search FAISS for hidden links
            core_fir = fir_neighbors[0]
            with torch.no_grad():
                emb = self.model.encode(self.data.x, self.data.edge_index)[core_fir:core_fir+1].cpu().numpy()
            norms = np.linalg.norm(emb, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            emb = emb / norms
            distances, indices = self.index.search(emb, top_k * 5)
            
            # Include the entity's known FIRs, plus the hidden ones FAISS found
            candidates = list(fir_neighbors[:5])
            for dist, idx in zip(distances[0], indices[0]):
                if self.node_types[idx] == 0 and idx not in candidates:
                    candidates.append(idx)
                if len(candidates) >= top_k:
                    break
                    
        if not candidates:
            print("  ❌ No related crimes found.")
            return
            
        print(f"  ✓ Found {len(candidates)} highly correlated structural candidates. Running Deep Inference...")
        
        core_fir = candidates[0]
        q_src = [core_fir] * (len(candidates) - 1)
        q_dst = candidates[1:]
        
        with torch.no_grad():
            struct_feats = self._compute_struct_feats(q_src, q_dst)
            z_all = self.model.encode(self.data.x, self.data.edge_index)
            z_src = z_all[q_src]
            z_dst = z_all[q_dst]
            
            logits = self.model.decoder(z_src, z_dst, struct_feats)
            probs = torch.sigmoid(logits).cpu().numpy().flatten()
            
        results = []
        feats = struct_feats.cpu().numpy()
        for i in range(len(q_dst)):
            prob = probs[i]
            same_mo = feats[i, 6] == 1.0
            same_beat = feats[i, 7] == 1.0
            same_dist = feats[i, 8] == 1.0
            jac_act = feats[i, 9]
            cn_io = feats[i, 5] > 0
            
            evidence = []
            if same_mo: evidence.append("Same MO")
            if same_beat: evidence.append("Same Beat")
            if same_dist: evidence.append("Same District")
            if jac_act > 0: evidence.append(f"Similar Acts (Jac: {jac_act:.2f})")
            if cn_io: evidence.append("Shared IO")
            ev_str = ", ".join(evidence) if evidence else "Network proximity only"
            
            results.append((self.id_to_name[q_dst[i]], prob, ev_str))
            
        results.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n🔥 Core Syndicate Analysis around {entity_name}")
        print(f"Primary Anchor FIR: {self.id_to_name[core_fir]}")
        print("="*85)
        for fir_name, prob, ev_str in results[:10]:
            print(f"  -> Link to {fir_name: <20} | Probability: {prob*100:05.2f}%")
            print(f"       └─ 📌 Evidence: {ev_str}")
        print("="*85)

    def query_new_fir(self, new_fir_dict, top_k=20):
        """Inductive inference for a brand new FIR JSON"""
        print(f"\n[Inductive Inference] Analyzing New FIR...")
        
        entities = []
        for k, v in new_fir_dict.items():
            if not v: continue
            if k == "CrimeHead_Name": entities.append(f"MO_{v}")
            elif k == "Beat_Name": entities.append(f"BEAT_{v}")
            elif k == "UnitName": entities.append(f"UNIT_{v}")
            elif k == "District_Name": entities.append(f"DIST_{v}")
            elif k == "ActSection": entities.append(f"ACT_{v}")
            elif k == "IOName": entities.append(f"IO_{v}")
            
        valid_entity_ids = []
        for e in entities:
            if e in self.name_to_id:
                valid_entity_ids.append(self.name_to_id[e])
                
        if not valid_entity_ids:
            print("  ❌ No recognized entities in the new FIR to anchor to the graph.")
            return
            
        print(f"  ✓ Anchoring to {len(valid_entity_ids)} existing entities...")
        
        # 2. Inductive Forward Pass (Zero-Shot)
        N = self.data.x.size(0)
        new_x = torch.zeros((1, 10), dtype=torch.float32).to(self.device)
        new_x[0, 0] = 1.0 # Type FIR
        
        full_x = torch.cat([self.data.x, new_x], dim=0)
        
        new_src = torch.tensor([N] * len(valid_entity_ids) + valid_entity_ids, dtype=torch.long)
        new_dst = torch.tensor(valid_entity_ids + [N] * len(valid_entity_ids), dtype=torch.long)
        
        new_edges = torch.stack([new_src, new_dst], dim=0).to(self.device)
        full_edge_index = torch.cat([self.data.edge_index, new_edges], dim=1)
        
        print("  Generating Zero-Shot Subgraph Embedding...")
        with torch.no_grad():
            z_all = self.model.encode(full_x, full_edge_index)
            z_new = z_all[-1:]
            
        emb = z_new.cpu().numpy()
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        emb = emb / norms
        
        print("  Searching FAISS for historical structural matches...")
        distances, indices = self.index.search(emb, top_k * 5)
        
        candidates = []
        for dist, idx in zip(distances[0], indices[0]):
            if self.node_types[idx] == 0: # FIR
                candidates.append(idx)
            if len(candidates) == top_k:
                break
                
        print(f"  ✓ Deep Interrogation of Top {len(candidates)} Suspect Crimes...")
        q_src = [N] * len(candidates)
        q_dst = candidates
        
        exact_feats = []
        for cand in q_dst:
            cand_neighbors = self.adj.indices[self.adj.indptr[cand]:self.adj.indptr[cand+1]]
            shared = set(valid_entity_ids).intersection(set(cand_neighbors))
            
            same_mo = 1.0 if any(self.id_to_name[x].startswith("MO_") for x in shared) else 0.0
            same_beat = 1.0 if any(self.id_to_name[x].startswith("BEAT_") for x in shared) else 0.0
            same_dist = 1.0 if any(self.id_to_name[x].startswith("DIST_") or self.id_to_name[x].startswith("UNIT_") for x in shared) else 0.0
            
            cand_acts = sum(1 for x in cand_neighbors if self.id_to_name[x].startswith("ACT_"))
            my_acts = sum(1 for x in valid_entity_ids if self.id_to_name[x].startswith("ACT_"))
            shared_acts = sum(1 for x in shared if self.id_to_name[x].startswith("ACT_"))
            union_acts = cand_acts + my_acts - shared_acts
            jac_act = shared_acts / union_acts if union_acts > 0 else 0.0
            
            cn_mo = sum(1 for x in shared if self.id_to_name[x].startswith("MO_"))
            cn_cg = sum(1 for x in shared if self.id_to_name[x].startswith("CG_"))
            cn_act = shared_acts
            cn_beat = sum(1 for x in shared if self.id_to_name[x].startswith("BEAT_"))
            cn_area = sum(1 for x in shared if self.id_to_name[x].startswith("AREA_"))
            cn_io = sum(1 for x in shared if self.id_to_name[x].startswith("IO_"))
            
            exact_feats.append([same_mo, same_beat, same_dist, jac_act, cn_mo, cn_cg, cn_act, cn_beat, cn_area, cn_io])
            
        struct_feats = torch.tensor(exact_feats, dtype=torch.float32).to(self.device)
        
        with torch.no_grad():
            z_src = z_new.expand(len(candidates), -1)
            z_dst = z_all[q_dst]
            logits = self.model.decoder(z_src, z_dst, struct_feats)
            probs = torch.sigmoid(logits).cpu().numpy().flatten()
            
        results = []
        feats = struct_feats.cpu().numpy()
        for i in range(len(q_dst)):
            prob = probs[i]
            same_mo = feats[i, 6] == 1.0
            same_beat = feats[i, 7] == 1.0
            same_dist = feats[i, 8] == 1.0
            jac_act = feats[i, 9]
            cn_io = feats[i, 5] > 0
            
            evidence = []
            if same_mo: evidence.append("Same MO")
            if same_beat: evidence.append("Same Beat")
            if same_dist: evidence.append("Same District")
            if jac_act > 0: evidence.append(f"Similar Acts (Jac: {jac_act:.2f})")
            if cn_io: evidence.append("Shared IO")
            ev_str = ", ".join(evidence) if evidence else "Network proximity only"
            
            results.append((self.id_to_name[q_dst[i]], prob, ev_str))
            
        results.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n🚨 [PREDICTION] Top Criminal Syndicate Matches for New Crime")
        print("="*85)
        for fir_name, prob, ev_str in results[:10]:
            print(f"  -> Historical Match: {fir_name: <20} | Confidence: {prob*100:05.2f}%")
            print(f"       └─ 📌 Evidence: {ev_str}")
        print("="*85)

    def evaluate_syndicate(self, fir_list):
        """Explicitly evaluate a 'self-made gang' / list of FIRs to prove the model finds the hidden links."""
        print(f"\n[Syndicate Evaluation] Interrogating {len(fir_list)} FIRs for hidden links...")
        valid_firs = []
        for f in fir_list:
            if f.strip() in self.name_to_id:
                valid_firs.append(self.name_to_id[f.strip()])
            else:
                print(f"  ❌ Warning: FIR '{f.strip()}' not found in database. Skipping.")
                
        if len(valid_firs) < 2:
            print("  ❌ Need at least 2 valid FIRs to evaluate links.")
            return
            
        # Build all pairs
        q_src, q_dst = [], []
        for i in range(len(valid_firs)):
            for j in range(i + 1, len(valid_firs)):
                q_src.append(valid_firs[i])
                q_dst.append(valid_firs[j])
                
        print(f"  ✓ Generating Exact Match & Topology features for {len(q_src)} pairs...")
        with torch.no_grad():
            struct_feats = self._compute_struct_feats(q_src, q_dst)
            z_all = self.model.encode(self.data.x, self.data.edge_index)
            z_src = z_all[q_src]
            z_dst = z_all[q_dst]
            
            logits = self.model.decoder(z_src, z_dst, struct_feats)
            probs = torch.sigmoid(logits).cpu().numpy().flatten()
            
        print(f"\n🚨 [PROOF] Hidden Link Probabilities for Self-Made Gang")
        print("="*85)
        feats = struct_feats.cpu().numpy()
        for i in range(len(probs)):
            src_name = self.id_to_name[q_src[i]]
            dst_name = self.id_to_name[q_dst[i]]
            prob = probs[i]
            
            # Extract Evidence
            same_mo = feats[i, 6] == 1.0
            same_beat = feats[i, 7] == 1.0
            same_dist = feats[i, 8] == 1.0
            jac_act = feats[i, 9]
            
            cn_io = feats[i, 5] > 0
            
            evidence = []
            if same_mo: evidence.append("Same MO")
            if same_beat: evidence.append("Same Beat")
            if same_dist: evidence.append("Same District")
            if jac_act > 0: evidence.append(f"Similar Acts (Jac: {jac_act:.2f})")
            if cn_io: evidence.append("Shared IO")
            
            ev_str = ", ".join(evidence) if evidence else "No direct exact matches found."
            
            # Highlight highly probable links
            status = "🔗 HIGH CONFIDENCE LINK" if prob > 0.85 else "   Weak Link"
            print(f"  {src_name: <15} <---> {dst_name: <15} | Prob: {prob*100:05.2f}% | {status}")
            print(f"    └─ 📌 Evidence: {ev_str}")
        print("="*85)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, help="Entity Name (e.g. 'IO_188800039') or 'FIR'")
    parser.add_argument("--json-mode", action="store_true",
                        help="Read a JSON payload from stdin and output a JSON response to stdout.")
    args = parser.parse_args()

    inv = InvestigatorSystem()

    # ─── JSON Mode (Backend Bridge) ──────────────────────────────────────────
    if args.json_mode:
        import rapidfuzz.process as rfuzz

        # Build a flat list of all known graph node names for fuzzy matching
        _all_node_names = list(inv.name_to_id.keys())

        def resolve_entity(graph_key: str) -> tuple[str | None, bool]:
            """
            Attempts exact match first, then fuzzy match.
            Returns (resolved_graph_key, was_exact_match).
            """
            if graph_key in inv.name_to_id:
                return graph_key, True
            # Try fuzzy match (only within same prefix namespace)
            prefix = graph_key.split("_")[0] + "_"
            candidates = [n for n in _all_node_names if n.startswith(prefix)]
            if not candidates:
                return None, False
            best, score, _ = rfuzz.extractOne(graph_key, candidates)
            if score >= 60:  # minimum 60% similarity required
                return best, False
            return None, False

        raw_payload = sys.stdin.read().strip()
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "error", "message": f"Invalid JSON input: {e}"}))
            sys.exit(1)

        mode = payload.get("mode", "query")

        # ── Gang Evaluation Mode ──────────────────────────────────────────────
        if mode == "gang":
            fir_ids = payload.get("fir_ids", [])
            threshold = float(payload.get("threshold", 0.0))

            valid_firs = [f for f in fir_ids if f in inv.name_to_id]
            invalid_firs = [f for f in fir_ids if f not in inv.name_to_id]

            if len(valid_firs) < 2:
                print(json.dumps({
                    "status": "error",
                    "message": f"Need at least 2 valid FIR IDs. Unrecognized: {invalid_firs}"
                }))
                sys.exit(1)

            q_src, q_dst = [], []
            for i in range(len(valid_firs)):
                for j in range(i + 1, len(valid_firs)):
                    q_src.append(inv.name_to_id[valid_firs[i]])
                    q_dst.append(inv.name_to_id[valid_firs[j]])

            pairs = []
            with torch.no_grad():
                struct_feats = inv._compute_struct_feats(q_src, q_dst)
                z_all = inv.model.encode(inv.data.x, inv.data.edge_index)
                z_src = z_all[q_src]
                z_dst = z_all[q_dst]
                logits = inv.model.decoder(z_src, z_dst, struct_feats)
                probs = torch.sigmoid(logits).cpu().numpy().flatten()

            feats = struct_feats.cpu().numpy()
            for i in range(len(probs)):
                prob = float(probs[i])
                if prob < threshold:
                    continue

                same_mo   = bool(feats[i, 6] == 1.0)
                same_beat = bool(feats[i, 7] == 1.0)
                same_dist = bool(feats[i, 8] == 1.0)
                jac_act   = float(feats[i, 9])
                cn_io     = bool(feats[i, 5] > 0)

                evidence = []
                if same_mo:   evidence.append("Same MO")
                if same_beat: evidence.append("Same Beat")
                if same_dist: evidence.append("Same District")
                if jac_act > 0: evidence.append(f"Similar Acts (Jac: {jac_act:.2f})")
                if cn_io:     evidence.append("Shared IO")
                if not evidence: evidence.append("Network proximity only")

                pairs.append({
                    "fir_a": inv.id_to_name[q_src[i]],
                    "fir_b": inv.id_to_name[q_dst[i]],
                    "probability": round(prob, 4),
                    "evidence": evidence,
                    "is_high_confidence": prob >= 0.85,
                })

            pairs.sort(key=lambda x: x["probability"], reverse=True)
            print(json.dumps({
                "status": "ok",
                "pairs": pairs,
                "unrecognized_firs": invalid_firs,
            }))
            sys.exit(0)

        # ── FIR Entity Query Mode ─────────────────────────────────────────────
        else:  # mode == "query"
            raw_entity_keys = payload.get("entities", [])

            matched_entities = []
            unmatched_fields = []

            # Resolve each entity key (exact or fuzzy)
            resolved_ids = []
            for raw_key in raw_entity_keys:
                resolved, exact = resolve_entity(raw_key)
                if resolved:
                    resolved_ids.append(inv.name_to_id[resolved])
                    label = resolved if exact else f"{resolved} (fuzzy from: {raw_key})"
                    matched_entities.append(label)
                else:
                    unmatched_fields.append(raw_key)

            if not resolved_ids:
                print(json.dumps({
                    "status": "error",
                    "message": "None of the provided entities could be resolved in the graph.",
                    "matched_entities": [],
                    "unmatched_fields": unmatched_fields,
                    "results": [],
                }))
                sys.exit(1)

            # Build a virtual FIR node connected to all resolved entities
            N = inv.data.x.size(0)
            new_x = torch.zeros((1, 10), dtype=torch.float32).to(inv.device)
            new_x[0, 0] = 1.0  # type = FIR

            full_x = torch.cat([inv.data.x, new_x], dim=0)
            new_src = torch.tensor([N] * len(resolved_ids) + resolved_ids, dtype=torch.long)
            new_dst = torch.tensor(resolved_ids + [N] * len(resolved_ids), dtype=torch.long)
            new_edges = torch.stack([new_src, new_dst], dim=0).to(inv.device)
            full_edge_index = torch.cat([inv.data.edge_index, new_edges], dim=1)

            with torch.no_grad():
                z_all = inv.model.encode(full_x, full_edge_index)
            z_new = z_all[N:N+1]

            # FAISS: find top-20 structurally similar FIR nodes
            query_vec = z_new.cpu().numpy().astype("float32")
            distances, indices = inv.index.search(query_vec, 50)

            candidates = []
            for _, idx in zip(distances[0], indices[0]):
                if inv.node_types[idx] == 0:
                    candidates.append(int(idx))
                if len(candidates) >= 20:
                    break

            if not candidates:
                print(json.dumps({
                    "status": "ok",
                    "matched_entities": matched_entities,
                    "unmatched_fields": unmatched_fields,
                    "results": [],
                }))
                sys.exit(0)

            q_src_list = [N] * len(candidates)
            q_dst_list = candidates

            # We can't use _compute_struct_feats for the virtual node,
            # so compute entity match features using resolved_ids directly
            exact_feats_list = []
            for cand in q_dst_list:
                cand_nbrs = set(inv.adj.indices[inv.adj.indptr[cand]:inv.adj.indptr[cand+1]])
                shared = set(resolved_ids).intersection(cand_nbrs)

                same_mo   = 1.0 if any(inv.id_to_name.get(x,"").startswith("MO_")   for x in shared) else 0.0
                same_beat = 1.0 if any(inv.id_to_name.get(x,"").startswith("BEAT_") for x in shared) else 0.0
                same_dist = 1.0 if any(inv.id_to_name.get(x,"").startswith("DIST_") for x in shared) else 0.0

                cand_acts   = sum(1 for x in inv.adj.indices[inv.adj.indptr[cand]:inv.adj.indptr[cand+1]] if inv.id_to_name.get(x,"").startswith("ACT_"))
                my_acts     = sum(1 for x in resolved_ids if inv.id_to_name.get(x,"").startswith("ACT_"))
                shared_acts = sum(1 for x in shared if inv.id_to_name.get(x,"").startswith("ACT_"))
                union_acts  = cand_acts + my_acts - shared_acts
                jac_act     = shared_acts / union_acts if union_acts > 0 else 0.0

                cn_mo   = sum(1 for x in shared if inv.id_to_name.get(x,"").startswith("MO_"))
                cn_cg   = sum(1 for x in shared if inv.id_to_name.get(x,"").startswith("CG_"))
                cn_act  = shared_acts
                cn_beat = sum(1 for x in shared if inv.id_to_name.get(x,"").startswith("BEAT_"))
                cn_area = sum(1 for x in shared if inv.id_to_name.get(x,"").startswith("AREA_"))
                cn_io   = sum(1 for x in shared if inv.id_to_name.get(x,"").startswith("IO_"))

                train_vmax = {"MO": 52.0, "CG": 1.0, "ACT": 1.0, "BEAT": 1.0, "AREA": 1.0, "IO": 5111.0}
                cn_scaled = [
                    np.log1p(cn_mo)   / np.log1p(train_vmax["MO"]   + 1),
                    np.log1p(cn_cg)   / np.log1p(train_vmax["CG"]   + 1),
                    np.log1p(cn_act)  / np.log1p(train_vmax["ACT"]  + 1),
                    np.log1p(cn_beat) / np.log1p(train_vmax["BEAT"] + 1),
                    np.log1p(cn_area) / np.log1p(train_vmax["AREA"] + 1),
                    np.log1p(cn_io)   / np.log1p(train_vmax["IO"]   + 1),
                ]
                exact_feats_list.append(cn_scaled + [same_mo, same_beat, same_dist, jac_act])

            struct_feats = torch.tensor(exact_feats_list, dtype=torch.float32).to(inv.device)

            with torch.no_grad():
                z_src_t = z_new.expand(len(candidates), -1)
                z_dst_t = z_all[q_dst_list]
                logits = inv.model.decoder(z_src_t, z_dst_t, struct_feats)
                probs = torch.sigmoid(logits).cpu().numpy().flatten()

            feats = struct_feats.cpu().numpy()
            results = []
            for i in range(len(candidates)):
                prob = float(probs[i])
                same_mo_   = bool(feats[i, 6] == 1.0)
                same_beat_ = bool(feats[i, 7] == 1.0)
                same_dist_ = bool(feats[i, 8] == 1.0)
                jac_act_   = float(feats[i, 9])
                cn_io_     = bool(feats[i, 5] > 0)

                evidence = []
                if same_mo_:   evidence.append("Same MO")
                if same_beat_: evidence.append("Same Beat")
                if same_dist_: evidence.append("Same District")
                if jac_act_ > 0: evidence.append(f"Similar Acts (Jac: {jac_act_:.2f})")
                if cn_io_:     evidence.append("Shared IO")
                if not evidence: evidence.append("Network proximity only")

                results.append({
                    "fir_id": inv.id_to_name[candidates[i]],
                    "probability": round(prob, 4),
                    "evidence": evidence,
                })

            results.sort(key=lambda x: x["probability"], reverse=True)
            print(json.dumps({
                "status": "ok",
                "matched_entities": matched_entities,
                "unmatched_fields": unmatched_fields,
                "results": results,
            }))
            sys.exit(0)

    # ─── Interactive / CLI Mode (unchanged) ──────────────────────────────────
    elif args.query == "FIR":
        new_fir = {
            "CrimeHead_Name": "MURDER",
            "Beat_Name": "TOWN BEAT",
            "UnitName": "HARIHARA TOWN PS",
            "District_Name": "DAVANAGERE",
            "ActSection": "IPC 1860 302",
            "IOName": "BASAVARAJA"
        }
        inv.query_new_fir(new_fir)
    elif args.query:
        inv.query_entity(args.query)
    else:
        print("Interactive Investigator Console (Type 'exit' to quit)")
        print("Tip 1: Type an Entity string (e.g. IO_188800039 or FIR_100) to interrogate it.")
        print("Tip 2: Paste a JSON dict to test inductive inference on a brand new FIR.")
        print("Tip 3: Type 'EVAL_GANG FIR_1, FIR_2, FIR_3' to test your self-made hidden syndicates!")
        while True:
            cmd = input("\nInvestigator> ").strip()
            if cmd == "exit": break
            if not cmd: continue

            if cmd.startswith("{"):
                try:
                    fir_dict = json.loads(cmd)
                    inv.query_new_fir(fir_dict)
                except Exception as e:
                    print(f"Invalid JSON: {e}")
            elif cmd.startswith("EVAL_GANG"):
                firs = cmd.replace("EVAL_GANG", "").split(",")
                inv.evaluate_syndicate(firs)
            else:
                inv.query_entity(cmd)

