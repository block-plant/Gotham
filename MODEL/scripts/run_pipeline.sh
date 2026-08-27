#!/bin/bash
set -e
export PYTHONPATH=.

echo "========================================================"
echo " 🚨 AI CRIMINAL LINKAGE & SYNDICATE INVESTIGATOR 🚨"
echo "========================================================"

echo "[Step 1/5] Extracting Real Police Entities & Demographics..."
python src/data_processing/hybrid_extractor.py

echo "[Step 2/5] Compiling Disk-Backed Multi-Relational Graph..."
python src/graph_builder/compile_large_graph.py

echo "[Step 3/5] Building 404-Dim Detective Features & NLP Embeddings..."
python src/graph_builder/build_features.py

echo "[Step 4/5] Mining Syndicate Links & Hard Negatives..."
python src/graph_builder/export_labels.py

echo "[Step 5/5] Training Multi-Scale GNN Link Predictor..."
python -m src.models.train --hidden-channels 256 --epochs 60

echo "[Finalizing] Exporting FAISS Embedding Index..."
python -m src.models.export_faiss

echo "========================================================"
echo "✓ PIPELINE COMPLETE! Ready for detective queries:"
echo "  python search.py --text \"Armed snatching near bus stand\""
echo "  python search.py --interactive"
echo "========================================================"
