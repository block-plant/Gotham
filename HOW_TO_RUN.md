# GNN Criminal Investigation System — Complete Guide

This system reads police reports (FIRs), builds a giant web of people, phones, vehicles, and locations, and trains an AI to find hidden criminal connections. Once trained, a police officer can type any name and get a ranked list of potential criminal links — along with a confidence score.

---

## 1. What You Need First

Make sure you have Python (Anaconda recommended). Then install all dependencies:

```bash
pip install -r requirements.txt
pip install faiss-cpu
pip install lmdb
python -m spacy download en_core_web_sm
```

**Minimum specs:**
- RAM: 8 GB (for 50K FIRs). 32 GB+ for 1 Crore FIRs.
- Disk: At least 5 GB free (for the binary graph files).
- Python 3.10+

---

## 2. The Full Pipeline (Run These Steps In Order)

---

### Step 1 — Generate Fake FIR Reports (for testing)

Creates realistic synthetic police reports with hidden gang connections baked in.

```bash
python data_processing/generate_narratives.py
```

**Output:** `entropy_narratives.txt` — one FIR per line (50,000 by default).

**To change the count**, open the file and change the `NUM_FIRS` variable.

---

### Step 2 — Extract Entities from Reports

Reads every report and pulls out:
- Person names + their anonymous ID (e.g. `P_abc123...`)
- Phone numbers
- Vehicle numbers
- Locations / landmarks
- FIR section numbers (laws used)
- Weapons mentioned

```bash
python data_processing/extractor.py
```

**Output:** `extracted_graph_nodes.jsonl` — each line is one FIR broken into structured data.

---

### Step 3 — (Optional) Patch Missing Metadata

If the extracted file is missing FIR IDs or timestamps, this fills the gaps.

```bash
python data_processing/patch_jsonl_metadata.py
```

---

### Step 4 — Compile the Graph

Turns all extracted entities into a graph. Every person, phone, vehicle, location and FIR becomes a **node**. Every connection between them becomes an **edge**.

```bash
python graph_builder/compile_large_graph.py
```

**Output (inside `graph_tensors/`):**
- `node_mapping.lmdb` — maps every name/phone/vehicle to a unique row ID
- `edge_src.bin` / `edge_dst.bin` — the edges stored as binary arrays on disk

> **1 Crore+ Note:** The system uses LMDB (disk-backed database) and binary memory-mapped arrays. Your RAM stays flat regardless of dataset size.

---

### Step 5 — Build Node Features

The AI model needs numbers, not strings. This builds a **16-dimensional** feature vector for every node by scanning the JSONL and edge binaries:

| Dims   | Feature                    | Purpose                                      |
|--------|----------------------------|----------------------------------------------|
| 0–6    | Node type (one-hot)        | FIR / Person / Phone / Vehicle / Law / Location / Weapon |
| 7      | Log-degree (normalised)    | Hub detection — gang leaders have high degree |
| 8      | Degree percentile          | Relative connectivity within the full graph   |
| 9      | Multi-FIR flag             | Recidivist / repeat location signal           |
| 10     | Crime severity             | Mean BNS section number (normalised)          |
| 11     | Co-accused density         | How many people share FIRs with this node     |
| 12–14  | SHA-256 name hash (3 floats) | Unique fingerprint — prevents embedding collapse |
| 15     | Reserved                   | Zero (future use)                             |

```bash
python graph_builder/build_features.py
```

**Output:** `graph_tensors/node_features.bin` (16 floats per node), `graph_meta.json` updated with `num_features: 16`

---

### Step 6 — Create Training Labels

Generates positive examples ("these two nodes ARE connected") and hard negative examples ("these two look similar but are NOT connected"). Hard negatives prevent the model from falsely linking innocent people.

```bash
python graph_builder/export_labels.py
```

**Output:** `graph_tensors/link_labels.pt`

---

### Step 7 — Train the AI Model

The AI (Graph Attention Network + Jumping Knowledge) learns from the graph. It weighs every connection mathematically to understand what a real criminal link looks like vs a coincidence.

```bash
python -m models.train --epochs 15 --batch-size 2048
```

**What you will see during training:**

```
Epoch 01 | loss=0.6512 | ROC-AUC=0.9925 | AP=0.9958
Epoch 02 | loss=0.5326 | ROC-AUC=0.9932 | AP=0.9960
...
Epoch 14 | loss=0.3556 | ROC-AUC=0.9979 | AP=0.9985
Best checkpoint saved to graph_tensors/link_predictor.pt (AP=0.9985)
```

**Output:** `graph_tensors/link_predictor.pt` — the trained AI brain.

> **1 Crore+ Note:** For massive graphs, add `--loader mini` to switch to mini-batch training.

---

### Step 8 — Export to Fast Search (FAISS)

Pre-computes a 128-dimension fingerprint vector for every single node and stores them in a FAISS vector database. After this, searching takes milliseconds — zero database calls.

```bash
python -m models.export_faiss
```

**Output:** `graph_tensors/node_embeddings.index`

---

## 3. How to Check and Verify Your Trained Model

### Check 1: Did training metrics improve each epoch?

```bash
cat train.log
```

**What to look for:**

| Metric | What it means | Target |
|--------|--------------|--------|
| `loss` | How wrong the model is on average | Should fall below 0.40 |
| `ROC-AUC` | Ability to tell "connected" from "not connected" | Above 0.95 (our model: **99.79%**) |
| `AP` (Average Precision) | Of all predicted links, how many are real | Above 0.95 (our model: **99.85%**) |

If ROC-AUC is stuck below 0.70 after 5 epochs:
- Increase `--epochs` to 25
- Reduce `--batch-size` to 512
- Delete `graph_tensors/link_labels.pt` and re-run Step 6 to regenerate labels

---

### Check 2: Verify the FAISS index is healthy

```bash
python -c "
import faiss, os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
idx = faiss.read_index('graph_tensors/node_embeddings.index')
print(f'Total vectors in index: {idx.ntotal}')
print(f'Vector dimension: {idx.d}')
print('FAISS index is healthy!' if idx.ntotal > 0 else 'ERROR: Index is empty!')
"
```

Expected output:
```
Total vectors in index: 134137
Vector dimension: 128
FAISS index is healthy!
```

---

### Check 3: Inspect the model checkpoint

```bash
python -c "
import torch
ckpt = torch.load('graph_tensors/link_predictor.pt', map_location='cpu', weights_only=False)
print('Model details:')
for k, v in ckpt.items():
    if k != 'model_state':
        print(f'  {k}: {v}')
"
```

Expected output:
```
Model details:
  in_channels: 16
  hidden_channels: 128
  num_layers: 3
  best_ap: 0.99xx
  epoch: N
```

---

### Check 4: Run a live investigation query

```bash
python search.py --query "Aachal Aggarwal" --threshold 0.70
```

If the model is working, you will see a list of connected people with percentage scores.

---

## 4. Ready-Made Test Data (Real Names from the Dataset)

These are real entries extracted from the generated FIR dataset. Copy and paste them to test immediately:

### Person names
```
Aachal Aggarwal
Oviya Dhingra
Aachal Arora
```

### Phone numbers
```
6016912892
6027102707
6029728167
```

### FIR case IDs
```
FIR-000000
FIR-000001
FIR-000002
```

**Example test commands:**

```bash
# Find all people connected to this person with more than 70% confidence
python search.py --query "Aachal Aggarwal" --threshold 0.70

# Find all connections to this phone number
python search.py --query "6016912892" --threshold 0.50

# Cast a wide net - show weak connections too
python search.py --query "Oviya Dhingra" --threshold 0.30 --limit 30
```

---

## 5. Understanding the Probability Score

The score (0.0 to 1.0) is a cosine similarity between two AI fingerprints:

| Score | What it means |
|-------|--------------|
| `0.90 – 1.00` | Extremely high. Almost certainly linked (same gang, same incidents) |
| `0.70 – 0.89` | Strong connection. Very likely linked (shared phone, vehicle, or location) |
| `0.50 – 0.69` | Moderate connection. Worth investigating further |
| `0.30 – 0.49` | Weak connection. Might be indirect or coincidental |
| `< 0.30` | Very weak. Probably not meaningfully connected |

**Recommended threshold for operational use:** `0.65` — catches real links while filtering noise.

---

## 6. Folder Structure

```
GNN/
├── data_processing/          # Steps 1-3: Generate and clean FIR data
│   ├── generate_narratives.py
│   ├── extractor.py
│   └── patch_jsonl_metadata.py
│
├── graph_builder/            # Steps 4-6: Build the graph
│   ├── compile_large_graph.py
│   ├── graph_io.py
│   ├── build_features.py
│   └── export_labels.py
│
├── models/                   # Steps 7-8: AI training and search export
│   ├── model.py              # GAT + Jumping Knowledge architecture
│   ├── dataloader.py         # Feeds data to model during training
│   ├── train.py              # Training loop with hard negative mining
│   ├── explainer.py          # Explains WHY a connection was found
│   └── export_faiss.py       # Exports vectors to FAISS database
│
├── tools/                    # Investigation utilities
│   ├── cms.py                # Case Management System
│   ├── forensic.py           # Law section and field extraction
│   ├── investigate.py        # Quick lookup by name/phone/ID
│   └── quick_visualizer.py   # Visual graph explorer
│
├── search.py                 # Main investigation CLI tool
├── graph_tensors/            # All compiled data lives here (auto-generated)
│   ├── node_mapping.lmdb     # Name/Phone to Row ID database
│   ├── node_features.bin     # Feature vectors for all nodes
│   ├── link_labels.pt        # Training examples
│   ├── link_predictor.pt     # Trained model checkpoint
│   └── node_embeddings.index # FAISS search index
│
├── entropy_narratives.txt    # Generated FIR text (50,000 reports)
├── extracted_graph_nodes.jsonl
├── requirements.txt
└── HOW_TO_RUN.md             # This file
```

---

## 7. Quick Copy-Paste: Full Pipeline from Scratch

```bash
# Data generation and extraction
python data_processing/generate_narratives.py
python data_processing/extractor.py
python data_processing/patch_jsonl_metadata.py

# Graph compilation
python graph_builder/compile_large_graph.py
python graph_builder/build_features.py
python graph_builder/export_labels.py

# Training and deployment
python -m models.train --epochs 15 --batch-size 2048
python -m models.export_faiss

# Test
python search.py --query "Aachal Aggarwal" --threshold 0.70
```

---

## 8. Scaling to 1 Crore+ FIRs

| Component | 50K FIRs | 1 Crore FIRs |
|-----------|----------|--------------|
| Storage needed | ~200 MB | ~40 GB |
| RAM during training | ~2 GB | Use `--loader mini` flag |
| FAISS index type | `IndexFlatIP` (exact) | `IndexIVFFlat` (clustered, faster) |
| Training time | ~15 mins on CPU | GPU recommended |
| Search speed | under 50ms | under 50ms (FAISS scales to billions) |

No code changes are needed in the data pipeline. It streams from disk automatically. Only the training loader and FAISS index type need updating when you go above 10 million nodes.
