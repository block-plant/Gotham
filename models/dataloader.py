"""PyTorch Geometric loaders over disk-backed graph tensors."""
import os

import torch
from torch.utils.data import DataLoader, TensorDataset
from torch_geometric.data import Data

from graph_builder.graph_io import load_edge_index, load_node_features

try:
    import torch_geometric.typing as pyg_typing
    HAS_NEIGHBOR_SAMPLER = pyg_typing.WITH_PYG_LIB or pyg_typing.WITH_TORCH_SPARSE
except Exception:
    HAS_NEIGHBOR_SAMPLER = False

try:
    from torch_geometric.loader import LinkNeighborLoader
except ImportError:
    LinkNeighborLoader = None
    HAS_NEIGHBOR_SAMPLER = False


def build_graph_data(tensor_dir="graph_tensors"):
    edge_index, meta = load_edge_index(tensor_dir, symmetrize=True)
    x, _ = load_node_features(tensor_dir)
    if x.size(0) != meta["node_count"]:
        raise ValueError("Node feature count does not match graph metadata.")

    data = Data(x=x, edge_index=edge_index)
    data.num_nodes = meta["node_count"]
    return data, meta


class FullGraphLinkLoader:
    """Edge-minibatch loader using a full-graph forward pass.

    Works without pyg-lib/torch-sparse. Suitable for graphs up to ~500k nodes.
    """

    def __init__(self, data, edge_label_index, edge_label, batch_size=4096, shuffle=True):
        self.data = data
        self.dataset = TensorDataset(edge_label_index.t(), edge_label)
        self.loader = DataLoader(
            self.dataset,
            batch_size=batch_size,
            shuffle=shuffle,
        )

    def __iter__(self):
        for edge_pairs, labels in self.loader:
            edge_label_index = edge_pairs.t().contiguous()
            batch = self.data.clone()
            batch.edge_label_index = edge_label_index
            batch.edge_label = labels
            yield batch

    def __len__(self):
        return len(self.loader)


def _try_neighbor_loader(data, labels, split, batch_size, num_neighbors, num_workers):
    if not HAS_NEIGHBOR_SAMPLER or LinkNeighborLoader is None:
        return None
    return LinkNeighborLoader(
        data,
        num_neighbors=list(num_neighbors),
        edge_label_index=labels[f"{split}_edge_label_index"],
        edge_label=labels[f"{split}_edge_label"],
        batch_size=batch_size,
        shuffle=(split == "train"),
        num_workers=num_workers,
    )


def build_link_loaders(
    tensor_dir="graph_tensors",
    batch_size=512,
    num_neighbors=(10, 10),
    num_workers=0,
):
    labels_path = os.path.join(tensor_dir, "link_labels.pt")
    if not os.path.exists(labels_path):
        raise FileNotFoundError(f"{labels_path} not found. Run export_labels.py first.")

    labels = torch.load(labels_path, weights_only=False)
    data, meta = build_graph_data(tensor_dir)

    train_loader = _try_neighbor_loader(
        data, labels, "train", batch_size, num_neighbors, num_workers
    )
    val_loader = _try_neighbor_loader(
        data, labels, "val", batch_size, num_neighbors, num_workers
    )

    loader_mode = "LinkNeighborLoader"
    if train_loader is None or val_loader is None:
        loader_mode = "FullGraphLinkLoader"
        train_loader = FullGraphLinkLoader(
            data,
            labels["train_edge_label_index"],
            labels["train_edge_label"],
            batch_size=max(batch_size, 2048),
            shuffle=True,
        )
        val_loader = FullGraphLinkLoader(
            data,
            labels["val_edge_label_index"],
            labels["val_edge_label"],
            batch_size=max(batch_size, 2048),
            shuffle=False,
        )

    return data, train_loader, val_loader, labels, meta, loader_mode


if __name__ == "__main__":
    data, train_loader, val_loader, labels, meta, mode = build_link_loaders()
    batch = next(iter(train_loader))
    print(f"Loader mode: {mode}")
    print(f"Graph nodes: {meta['node_count']:,}, edges: {meta['edge_count']:,}")
    print(f"Batch x: {batch.x.shape}, edge_index: {batch.edge_index.shape}")
    print(f"Labeled edges in batch: {batch.edge_label.numel()}")
