# AI Criminal Linkage & Syndicate Investigator (Gotham GNN)

A Graph Neural Network (GNN) and NLP Intelligence system built over **1.67 Million Real Police FIR Records** (`kaggle_fir_data.csv`) to uncover invisible criminal linkages, repeat serial crime chains, and multi-station syndicates using modus operandi, legal statutes, spatial hierarchies, and co-offending dynamics.

---

## 🏛️ System Architecture

```
[ kaggle_fir_data.csv (1.67M Real FIRs) ]
               │
               ▼
   [ data_processing/hybrid_extractor.py ]
   ├── Modus Operandi (Crime Heads)
   ├── Legal Statutes (IPC / BNS / Special Acts)
   ├── Spatial Hierarchy (District -> Police Station -> Beat -> Area -> Landmarks)
   ├── Demographics (Accused, Arrested, Chargesheeted, Victims)
   └── Rich Investigative NLP Narrative
               │
               ▼
   [ graph_builder/compile_large_graph.py ]  ──>  LMDB & Memmap Graph Tensors
   [ graph_builder/build_features.py ]       ──>  404-Dim Feature Matrix (MiniLM NLP + Dynamics)
   [ graph_builder/export_labels.py ]        ──>  Syndicate Link Mining + Hard Negatives
               │
               ▼
   [ models/train.py ]                       ──>  Multi-Scale GAT + JumpingKnowledge GNN
   [ models/export_faiss.py ]                ──>  128-Dim Latent FAISS Cosine Index
               │
               ▼
   [ search.py ]                             ──>  Real-Time Detective Query & Syndicate Engine
```

---

## 🚀 1. Setup & Requirements

```bash
# Core dependencies
pip install torch torch-geometric sentence-transformers faiss-cpu scikit-learn lmdb numpy tqdm pyvis
```

---

## ⚡ 2. Running the Pipeline

Ensure `kaggle_fir_data.csv` is placed in the project root directory.

### On Linux / macOS / Bash:
```bash
chmod +x run_pipeline.sh
./run_pipeline.sh
```

### On Windows PowerShell:
```powershell
.\run_pipeline.ps1
```

### Or Step-by-Step:
```bash
# Step 1: Extract real entities and narratives
python data_processing/hybrid_extractor.py

# Step 2: Compile disk-backed graph tensors
python graph_builder/compile_large_graph.py

# Step 3: Build 404-dim detective features & SentenceTransformer embeddings
python graph_builder/build_features.py

# Step 4: Mine syndicate links and hard negatives
python graph_builder/export_labels.py

# Step 5: Train GNN Link Predictor
python -m models.train --hidden-channels 128 --batch-size 1024 --epochs 15

# Final: Export FAISS Latent Vector Index
python -m models.export_faiss
```

---

## 🕵️‍♂️ 3. Investigating Cases & Querying Real-Time Clues

### Option A: Query an Existing Case / Node
```bash
python search.py --query "FIR-1898733"
python search.py --query "MO_CHAIN_SNATCHING"
```

### Option B: Zero-Shot Raw FIR Text & Clue Querying
Pass any new unfiled incident, clue description, or plain English text:
```bash
python search.py --text "Armed motorcycle gang of 3 men snatched gold chain at bus stand under IPC 392"
python search.py --text "Cyber crime OTP phishing syndicate in Bengaluru City targeting bank accounts under IT Act 66D"
```

### Option C: Interactive Detective Console
```bash
python search.py --interactive
```

---

## 📊 4. Graph Visualization
Generate a browser-based interactive 3D/2D network graph of case links:
```bash
python tools/quick_visualizer.py
# Open police_graph_sample.html in any browser
```
