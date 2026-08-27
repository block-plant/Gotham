"""Advanced GNN encoder and link predictor for multi-scale crime graphs.

Key design decisions (v2 - 90%+ target):
  - Input LayerNorm: normalize the 788-dim mixed-scale features ONCE before any SAGEConv.
  - SAGEConv (not GATConv): avoids O(|E|) attention matrices on 40M-edge graph, stays in 23GB RAM.
  - Residual connections after every SAGEConv: prevents vanishing gradients in 4-layer deep encoder.
  - LayerNorm after each SAGEConv: stabilizes variance across heterogeneous node types.
  - JumpingKnowledge (cat): aggregates 1-hop (local crime) through 4-hop (syndicate network).
  - MLPDecoder with structural features: feeds precomputed Common Neighbors, Jaccard, Adamic-Adar
    directly into the decoder — these are the #1 discriminative signal for crime link prediction.
  - hidden_channels=384 with 4 layers: sufficient capacity without exceeding RAM budget.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, JumpingKnowledge

# 6 type-specific CN features [CN_MO, CN_CG, CN_ACT, CN_BEAT, CN_AREA, CN_IO]
# + 4 exact entity-match features [same_mo, same_beat, same_district, acts_jaccard]
STRUCT_DIM = 10



class AdvancedGNNEncoder(nn.Module):
    def __init__(self, in_channels, hidden_channels=384, num_layers=4, dropout=0.1, heads=4):
        super().__init__()
        self.dropout = dropout

        # Pre-normalize heterogeneous 788-dim input features per-node
        self.input_norm = nn.LayerNorm(in_channels)

        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        self.skips = nn.ModuleList()

        # Layer 0: in_channels -> hidden_channels, with linear skip projection
        self.convs.append(SAGEConv(in_channels, hidden_channels))
        self.norms.append(nn.LayerNorm(hidden_channels))
        self.skips.append(nn.Linear(in_channels, hidden_channels, bias=False))

        # Layers 1..num_layers-1: hidden -> hidden, with identity skip
        for _ in range(num_layers - 1):
            self.convs.append(SAGEConv(hidden_channels, hidden_channels))
            self.norms.append(nn.LayerNorm(hidden_channels))
            self.skips.append(nn.Identity())

        # Jumping Knowledge: concat all hop embeddings for rich multi-scale repr
        self.jk = JumpingKnowledge(mode="cat")
        self.lin = nn.Linear(hidden_channels * num_layers, hidden_channels)

    def forward(self, x, edge_index):
        x = self.input_norm(x)
        x_in = x
        xs = []
        for conv, norm, skip in zip(self.convs, self.norms, self.skips):
            x_new = conv(x_in, edge_index)
            x_new = norm(x_new)
            x_new = x_new + skip(x_in)   # residual connection
            x_new = F.elu(x_new)
            x_new = F.dropout(x_new, p=self.dropout, training=self.training)
            xs.append(x_new)
            x_in = x_new

        x = self.jk(xs)
        x = self.lin(x)
        return x


class MLPDecoder(nn.Module):
    """Expressive MLP Decoder with structural edge features.

    Takes per-edge structural similarity signals (Common Neighbors normalized,
    Jaccard coefficient, Adamic-Adar normalized) precomputed from the graph
    topology and concatenates them with the learned node embedding interactions.

    This gives the decoder explicit graph-structural evidence beyond what the
    GNN encoder can capture in a fixed number of hops.
    """
    def __init__(self, hidden_channels, struct_dim=STRUCT_DIM):
        super().__init__()
        # Input: [abs(z_src - z_dst) | z_src * z_dst | struct_feats]
        self.lin1 = nn.Linear(hidden_channels * 2 + struct_dim, hidden_channels)
        self.norm = nn.LayerNorm(hidden_channels)
        self.lin2 = nn.Linear(hidden_channels, 1)

    def forward(self, z_src, z_dst, struct_feats=None):
        diff = torch.abs(z_src - z_dst)
        mult = z_src * z_dst
        if struct_feats is not None:
            h = torch.cat([diff, mult, struct_feats.to(z_src.device)], dim=-1)
        else:
            # Fallback: zero-pad structural slot (inference without precomputed feats)
            zeros = torch.zeros(z_src.shape[0], STRUCT_DIM, device=z_src.device)
            h = torch.cat([diff, mult, zeros], dim=-1)

        h = self.lin1(h)
        h = self.norm(h)
        h = F.elu(h)
        return self.lin2(h).squeeze(-1)


class LinkPredictor(nn.Module):
    def __init__(self, in_channels, hidden_channels=384, num_layers=4, dropout=0.1, heads=4):
        super().__init__()
        self.encoder = AdvancedGNNEncoder(
            in_channels=in_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
            heads=heads,
        )
        self.decoder = MLPDecoder(hidden_channels, struct_dim=STRUCT_DIM)

    def encode(self, x, edge_index):
        return self.encoder(x, edge_index)

    def decode(self, z, edge_label_index, struct_feats=None):
        src = z[edge_label_index[0]]
        dst = z[edge_label_index[1]]
        return self.decoder(src, dst, struct_feats)

    def forward(self, x, edge_index, edge_label_index, struct_feats=None):
        z = self.encode(x, edge_index)
        return self.decode(z, edge_label_index, struct_feats)
