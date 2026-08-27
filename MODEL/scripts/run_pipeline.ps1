# run_pipeline.ps1 - Windows PowerShell Pipeline Runner
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "."

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " AI CRIMINAL LINKAGE & SYNDICATE INVESTIGATOR " -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan

Write-Host "`n[Step 1/5] Extracting Real Police Entities & Demographics..." -ForegroundColor Green
python src/data_processing/hybrid_extractor.py

Write-Host "`n[Step 2/5] Compiling Disk-Backed Multi-Relational Graph..." -ForegroundColor Green
python src/graph_builder/compile_large_graph.py

Write-Host "`n[Step 3/5] Building 788-Dim Detective Features & NLP Embeddings..." -ForegroundColor Green
python src/graph_builder/build_features.py

Write-Host "`n[Step 4/5] Mining Syndicate Links & Hard Negatives..." -ForegroundColor Green
python src/graph_builder/export_labels.py

Write-Host "`n[Step 5/5] Training Multi-Scale GNN Link Predictor..." -ForegroundColor Green
python -m src.models.train --hidden-channels 256 --epochs 60

Write-Host "`n[Finalizing] Exporting FAISS Embedding Index..." -ForegroundColor Green
python -m src.models.export_faiss

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "PIPELINE COMPLETE! Ready for detective queries:" -ForegroundColor Yellow
Write-Host "  python search.py --text 'Armed snatching near bus stand'" -ForegroundColor White
Write-Host "  python search.py --interactive" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan
