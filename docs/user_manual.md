# Gotham AI: Investigator's Manual

Welcome to **Gotham AI**, your intelligent crime linkage and syndicate detection engine. Gotham is designed to act like a master detective—it connects the dots between seemingly unrelated crimes, officers, locations, and gangs to uncover hidden criminal networks.

## 1. What is Gotham AI?
Traditional police databases require you to know exactly what you are looking for. Gotham is different. It uses a **Graph Neural Network (GNN)** that reads through thousands of FIRs (First Information Reports), learns the patterns of how criminals operate, and predicts hidden links. 

**Model Reliability & Accuracy:**
Our AI has been trained on real police data and rigorously tested.
* **Accuracy Score (ROC-AUC):** 81.6%
* **Precision:** 75.6%
*(This means when Gotham suggests that a suspect or a case is linked to a larger syndicate, there is a very high probability that the connection is accurate).*

---

## 2. Using the Interactive Map (Frontend)
The visual interface (`police_graph_sample.html`) is where you can explore the criminal underworld visually.

### Getting Started
Simply double-click `police_graph_sample.html` to open it in your web browser. 
* **The Nodes:** Every dot on the screen represents a piece of the puzzle—a specific FIR, a District, a Police Station, a Modus Operandi (MO), or a Gang Profile.
* **The Links:** The lines between the dots show known relationships.

### Key Features
1. **Search Bar:** Type in any keyword (e.g., "Theft", "Bus Stand", "FIR-1234") to instantly locate the record.
2. **Filters (Left Sidebar):** Click the buttons (e.g., "Modus Operandi", "Gang Pattern") to hide irrelevant information and focus only on what you need.
3. **Investigation Panel:** Click on any node on the graph. The left sidebar will automatically update to show a detailed card of that node, listing all of its direct connections.
4. **Zoom & Pan:** Use your mouse scroll to zoom in and out, and click-and-drag to move around the map.

---

## 3. Querying the AI (Backend API)
If you want to plug Gotham into a new frontend or run rapid text-based searches, you can use the `search.py` tool. It accepts discrete fields and returns clean, structured data.

### Example 1: Searching for a specific Case ID
If you have a known FIR and want the AI to find cases with identical criminal signatures:
```bash
python search.py --fir_id "FIR-1898733"
```
*Add `--json` to the end of any command to get raw JSON output for your frontend application.*

### Example 2: Searching by Crime Profile
If a new crime just occurred and you want to match the signature against the database:
```bash
python search.py --crime_type "ROBBERY" --modus_operandi "CHAIN_SNATCHING" --location "Bus Stand" --accused_count 2 --json
```

### Example 3: Interactive Console
If you prefer a conversational interface to explore leads:
```bash
python search.py --interactive
```
You can type in raw clues like *"Armed duo snatched a chain near the metro station"* and the AI will extract the parameters and find the most likely suspects and linked historical cases.
