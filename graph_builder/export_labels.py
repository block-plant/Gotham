"""Export positive/negative link labels for syndicate link prediction."""
import json
import os
import random

import numpy as np
import torch

from graph_builder.graph_io import lookup_node_id, open_node_mapping

CHAIN_ENTITY_KEYS = ("persons", "phones", "vehicles")
POSITIVE_CATEGORIES = ("persons", "phones", "vehicles")


def _collect_record_entities(record):
    entities = record.get("entities", {})
    items = []
    for key in POSITIVE_CATEGORIES:
        items.extend(entities.get(key, []))
    return list(dict.fromkeys(items))


def _pairs_from_items(items):
    pairs = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            pairs.append((items[i], items[j]))
    return pairs


def export_link_labels(
    jsonl_path="extracted_graph_nodes.jsonl",
    tensor_dir="graph_tensors",
    val_ratio=0.2,
    seed=42,
):
    random.seed(seed)
    np.random.seed(seed)

    env = open_node_mapping(tensor_dir)
    positive_pairs = set()
    interaction_pairs = set()

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            is_chain = record.get("is_chain", False)

            if is_chain:
                items = _collect_record_entities(record)
                for a, b in _pairs_from_items(items):
                    positive_pairs.add(tuple(sorted((a, b))))

            for interaction in record.get("interactions", []):
                subj = interaction.get("subject")
                obj = interaction.get("object")
                if subj and obj and subj != obj:
                    interaction_pairs.add(tuple(sorted((subj, obj))))

    positive_pairs |= interaction_pairs

    mapped_positives = []
    for a, b in positive_pairs:
        src = lookup_node_id(env, a)
        dst = lookup_node_id(env, b)
        if src is None or dst is None or src == dst:
            continue
        mapped_positives.append((min(src, dst), max(src, dst)))

    mapped_positives = list(dict.fromkeys(mapped_positives))
    if not mapped_positives:
        raise RuntimeError("No positive link labels found. Re-run patch/compile pipeline.")

    random.shuffle(mapped_positives)
    split_idx = max(1, int(len(mapped_positives) * (1 - val_ratio)))
    train_pos = mapped_positives[:split_idx]
    val_pos = mapped_positives[split_idx:] or mapped_positives[-max(1, len(mapped_positives) // 5):]

    meta_path = os.path.join(tensor_dir, "graph_meta.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        node_count = json.load(f)["node_count"]

    existing_edges = set(mapped_positives)

    def sample_negatives(num_samples, forbidden):
        negatives = set()
        attempts = 0
        max_attempts = num_samples * 50
        while len(negatives) < num_samples and attempts < max_attempts:
            a = random.randint(0, node_count - 1)
            b = random.randint(0, node_count - 1)
            attempts += 1
            if a == b:
                continue
            pair = (min(a, b), max(a, b))
            if pair in forbidden or pair in negatives:
                continue
            negatives.add(pair)
        return list(negatives)

    train_neg = sample_negatives(len(train_pos), existing_edges)
    val_neg = sample_negatives(len(val_pos), existing_edges | set(train_neg))

    def pack_pairs(pairs, label):
        if not pairs:
            return torch.empty((2, 0), dtype=torch.long), torch.empty(0, dtype=torch.float)
        src, dst = zip(*pairs)
        edge_label_index = torch.tensor([src, dst], dtype=torch.long)
        edge_label = torch.full((len(pairs),), float(label), dtype=torch.float)
        return edge_label_index, edge_label

    train_pos_index, train_pos_label = pack_pairs(train_pos, 1.0)
    train_neg_index, train_neg_label = pack_pairs(train_neg, 0.0)
    val_pos_index, val_pos_label = pack_pairs(val_pos, 1.0)
    val_neg_index, val_neg_label = pack_pairs(val_neg, 0.0)

    payload = {
        "train_edge_label_index": torch.cat([train_pos_index, train_neg_index], dim=1),
        "train_edge_label": torch.cat([train_pos_label, train_neg_label], dim=0),
        "val_edge_label_index": torch.cat([val_pos_index, val_neg_index], dim=1),
        "val_edge_label": torch.cat([val_pos_label, val_neg_label], dim=0),
        "num_train_pos": len(train_pos),
        "num_train_neg": len(train_neg),
        "num_val_pos": len(val_pos),
        "num_val_neg": len(val_neg),
    }

    out_path = os.path.join(tensor_dir, "link_labels.pt")
    torch.save(payload, out_path)
    env.close()

    print(f"Saved link labels to {out_path}")
    print(
        f"Train: {len(train_pos)} pos / {len(train_neg)} neg | "
        f"Val: {len(val_pos)} pos / {len(val_neg)} neg"
    )
    return out_path


if __name__ == "__main__":
    export_link_labels()
