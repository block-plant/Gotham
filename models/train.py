"""Train GraphSAGE link predictor with ROC-AUC and Average Precision."""
import argparse
import os

import torch
import torch.nn.functional as F
from sklearn.metrics import average_precision_score, roc_auc_score

from models.dataloader import build_link_loaders
from graph_builder.graph_io import resolve_device
from models.model import LinkPredictor


def evaluate(model, loader, device):
    model.eval()
    ys = []
    preds = []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits = model(batch.x, batch.edge_index, batch.edge_label_index)
            probs = torch.sigmoid(logits).cpu().numpy()
            labels = batch.edge_label.cpu().numpy()
            preds.extend(probs.tolist())
            ys.extend(labels.tolist())

    if len(set(ys)) < 2:
        return {"roc_auc": 0.0, "average_precision": 0.0}

    return {
        "roc_auc": float(roc_auc_score(ys, preds)),
        "average_precision": float(average_precision_score(ys, preds)),
    }


def train(
    tensor_dir="graph_tensors",
    epochs=15,
    lr=1e-3,
    hidden_channels=128,
    num_layers=3,
    batch_size=512,
):
    device = resolve_device()
    data, train_loader, val_loader, labels, meta, loader_mode = build_link_loaders(
        tensor_dir=tensor_dir,
        batch_size=batch_size,
    )
    print(f"Training with {loader_mode}")

    model = LinkPredictor(
        in_channels=data.num_node_features,
        hidden_channels=hidden_channels,
        num_layers=num_layers,
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    best_ap = -1.0
    checkpoint_path = os.path.join(tensor_dir, "link_predictor.pt")

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_edges = 0

        for batch in train_loader:
            batch = batch.to(device)
            
            # --- HARD NEGATIVE MINING ---
            # Replace random global negatives with locally structured hard negatives
            pos_mask = batch.edge_label == 1.0
            neg_mask = ~pos_mask
            if neg_mask.any():
                num_neg = neg_mask.sum().item()
                # Sample negative destinations from within the locally connected subgraph batch
                hard_neg_dst = torch.randint(0, batch.num_nodes, (num_neg,), device=device)
                batch.edge_label_index[1, neg_mask] = hard_neg_dst
            # ----------------------------

            optimizer.zero_grad()
            logits = model(batch.x, batch.edge_index, batch.edge_label_index)
            loss = F.binary_cross_entropy_with_logits(logits, batch.edge_label)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * batch.edge_label.numel()
            total_edges += batch.edge_label.numel()

        metrics = evaluate(model, val_loader, device)
        avg_loss = total_loss / max(total_edges, 1)
        print(
            f"Epoch {epoch:02d} | loss={avg_loss:.4f} | "
            f"ROC-AUC={metrics['roc_auc']:.4f} | AP={metrics['average_precision']:.4f}"
        )

        if metrics["average_precision"] >= best_ap:
            best_ap = metrics["average_precision"]
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "hidden_channels": hidden_channels,
                    "num_layers": num_layers,
                    "in_channels": data.num_node_features,
                    "metrics": metrics,
                    "meta": meta,
                },
                checkpoint_path,
            )

    print(f"Best checkpoint saved to {checkpoint_path} (AP={best_ap:.4f})")
    return checkpoint_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tensor-dir", default="graph_tensors")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args()
    train(
        tensor_dir=args.tensor_dir,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
    )
