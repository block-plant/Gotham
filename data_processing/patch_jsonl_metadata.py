"""Backfill fir_id and is_chain on existing extracted JSONL without re-running spaCy."""
import json
import os
import shutil

CHAIN_LAWS = {"BNS 143", "BNS 103", "BNS 308"}


def patch_jsonl(input_path="extracted_graph_nodes.jsonl", output_path=None):
    if output_path is None:
        output_path = input_path + ".tmp"

    patched = 0
    with open(input_path, "r", encoding="utf-8") as src, open(output_path, "w", encoding="utf-8") as dst:
        for idx, line in enumerate(src):
            record = json.loads(line)
            if "fir_id" not in record:
                record["fir_id"] = f"FIR-{idx:06d}"
                patched += 1
            sections = record.get("entities", {}).get("legal_sections", [])
            record["is_chain"] = any(section in CHAIN_LAWS for section in sections)
            dst.write(json.dumps(record) + "\n")

    shutil.move(output_path, input_path)
    print(f"Patched {patched} records with fir_id; wrote is_chain flags to {input_path}")


if __name__ == "__main__":
    path = "extracted_graph_nodes.jsonl"
    if not os.path.exists(path):
        raise SystemExit(f"Missing {path}")
    patch_jsonl(path)
