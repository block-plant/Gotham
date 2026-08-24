"""Advanced GNN encoder and link predictor for multi-scale graphs."""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv, JumpingKnowledge


class AdvancedGNNEncoder(nn.Module):
    def __init__(self, in_channels, hidden_channels=128, num_layers=3, dropout=0.2, heads=4):
        super().__init__()
        self.dropout = dropout
        self.convs = nn.ModuleList()
        # Initial layer
        self.convs.append(GATConv(in_channels, hidden_channels // heads, heads=heads))
        # Deep layers to capture large syndicates
        for _ in range(num_layers - 1):
            self.convs.append(GATConv(hidden_channels, hidden_channels // heads, heads=heads))
            
        # Jumping Knowledge to dynamically combine 1-hop (small gangs) to N-hop (syndicates) structures
        self.jk = JumpingKnowledge(mode="cat")
        self.lin = nn.Linear(hidden_channels * num_layers, hidden_channels)

    def forward(self, x, edge_index):
        xs = []
        for conv in self.convs:
            x = conv(x, edge_index)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
            xs.append(x)
            
        x = self.jk(xs)
        x = self.lin(x)
        return x


class LinkPredictor(nn.Module):
    def __init__(self, in_channels, hidden_channels=128, num_layers=3, dropout=0.2):
        super().__init__()
        self.encoder = AdvancedGNNEncoder(
            in_channels=in_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )

    def encode(self, x, edge_index):
        return self.encoder(x, edge_index)

    def decode(self, z, edge_label_index):
        src = z[edge_label_index[0]]
        dst = z[edge_label_index[1]]
        return (src * dst).sum(dim=-1)

    def forward(self, x, edge_index, edge_label_index):
        z = self.encode(x, edge_index)
        return self.decode(z, edge_label_index)
