# quick_visualizer.py
import json
from pyvis.network import Network

net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
net.barnes_hut() # Physics engine to space out nodes cleanly

# Only load a small chunk so your browser doesn't freeze!
LIMIT = 500 

print("Building visualization network...")
with open("extracted_graph_nodes.jsonl", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= LIMIT: break
        record = json.loads(line)
        
        fir_node_id = record.get("fir_id", f"FIR-{i:06d}")
        
        # Add the central "FIR Hub" node
        net.add_node(fir_node_id, label=fir_node_id, color="#e0e0e0", shape="box")
        
        # 1. Link extracted entities (Persons, Phones, Vehicles, etc.) to the FIR Hub
        entities = record.get("entities", {})
        for cat, items in entities.items():
            for item in items:
                # Color code people differently from phones or vehicles
                node_color = "#3498db" if cat == "persons" else "#e74c3c"
                net.add_node(item, label=item, color=node_color)
                net.add_edge(item, fir_node_id, color="#555555")
                
        # 2. Add Subject-Verb-Object Interaction arrows if extracted by SpaCy
        interactions = record.get("interactions", [])
        for inter in interactions:
            subj = inter["subject"]
            action = inter["action"]
            obj = inter["object"]
            
            # Ensure nodes exist
            net.add_node(subj, label=subj, color="#2ecc71")
            net.add_node(obj, label=obj, color="#f1c40f")
            
            # Draw a directed edge labeled with the action (e.g., ASSAULT)
            net.add_edge(subj, obj, title=action, label=action, color="#e67e22", arrows="to")

print(f"Saving visualization to 'police_graph_sample.html'...")
net.show("police_graph_sample.html", notebook=False)
print("Done! Open 'police_graph_sample.html' in your web browser.")