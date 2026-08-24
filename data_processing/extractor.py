import spacy
import re
import json
import time

# 1. LOAD INDUSTRIAL NLP
# Using the 'sm' model for massive speed, but it still includes Dependency Parsing.
print("Loading NLP Engine...")
nlp = spacy.load("en_core_web_sm")

# 2. INDIAN LAW ENFORCEMENT REGEX MATCHERS
# Captures standard Indian formats (e.g., +91-9876543210, UP-32-AB-1234, BNS 308)
PATTERN_PHONE = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}")
PATTERN_VEHICLE = re.compile(r"[A-Z]{2}[\-\s]?\d{1,2}[\-\s]?[A-Z]{1,2}[\-\s]?\d{4}")
PATTERN_LAW = re.compile(r"(BNS|IPC|NDPS|Arms Act)[\-\s]?\d{2,3}[A-Z]?")
PATTERN_PERSON_ID = re.compile(r"\[ID:(P_[a-f0-9]+)\]", re.I)
PATTERN_WEAPON_ID = re.compile(r"\[Serial:(W_[a-f0-9]+)\]", re.I)
PATTERN_PHONE_TAG = re.compile(r"(PH_[a-f0-9]+)", re.I)
CHAIN_LAWS = {"BNS 143", "BNS 103", "BNS 308"}

# 3. RELATION EXTRACTION (Subject-Verb-Object)
def extract_triples(doc):
    """
    Reads the grammar tree to find actions. 
    Converts "Ramesh assaulted Suresh" into (Ramesh) -> [ASSAULTED] -> (Suresh)
    """
    triples = []
    for token in doc:
        if token.pos_ == "VERB":
            # Look for the subject (who did the action)
            subjects = [w.text for w in token.lefts if w.dep_ in ["nsubj", "nsubjpass"]]
            # Look for the object (who/what received the action)
            objects = [w.text for w in token.rights if w.dep_ in ["dobj", "pobj", "attr"]]
            
            if subjects and objects:
                triples.append({
                    "subject": subjects[0],
                    "action": token.lemma_.upper(), # e.g., 'assaulted' becomes 'ASSAULT'
                    "object": objects[0]
                })
    return triples

# 4. DATA EXTRACTION ENGINE
def process_document(doc, line_idx=None):
    """Extracts all entities, patterns, and complex relationships from a single text."""
    text = doc.text
    
    # Neural Entity Extraction
    persons = list(set([ent.text for ent in doc.ents if ent.label_ == "PERSON"]))
    locations = list(set([ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC", "FAC"]]))
    organizations = list(set([ent.text for ent in doc.ents if ent.label_ == "ORG"]))
    
    # Pattern Extraction
    phones = list(set(PATTERN_PHONE.findall(text)))
    vehicles = list(set(PATTERN_VEHICLE.findall(text)))
    legal_sections = list(set(m.group() for m in PATTERN_LAW.finditer(text)))
    person_ids = list(set(PATTERN_PERSON_ID.findall(text)))
    weapons = list(set(PATTERN_WEAPON_ID.findall(text)))
    phone_tags = list(set(PATTERN_PHONE_TAG.findall(text)))
    
    # Complex Relational Extraction
    interactions = extract_triples(doc)
    
    record = {
        "entities": {
            "persons": persons,
            "locations": locations,
            "organizations": organizations,
            "phones": phones,
            "vehicles": vehicles,
            "legal_sections": legal_sections,
            "person_ids": person_ids,
            "weapons": weapons,
            "phone_tags": phone_tags,
        },
        "interactions": interactions
    }
    if line_idx is not None:
        record["fir_id"] = f"FIR-{line_idx:06d}"
        record["is_chain"] = any(section in CHAIN_LAWS for section in legal_sections)
    return record

# 5. STREAMING ARCHITECTURE FOR 1 CRORE+ RECORDS
def batch_reader(file_path, batch_size=2000):
    """Reads a massive file in chunks to prevent memory overflow."""
    batch = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            batch.append(line.strip())
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

def run_extraction_pipeline(input_file, output_file):
    """Uses multi-processing to rip through text at maximum CPU speed."""
    start_time = time.time()
    total_processed = 0
    
    print(f"Starting highly-scalable extraction to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as out_f:
        # Stream data in batches of 2000
        for text_batch in batch_reader(input_file, batch_size=2000):
            # n_process=-1 uses 100% of available CPU cores automatically
            docs = nlp.pipe(text_batch, n_process=-1)
            
            for doc in docs:
                extracted_data = process_document(doc, line_idx=total_processed)
                # Instantly write to disk to clear RAM
                out_f.write(json.dumps(extracted_data) + "\n")
                total_processed += 1
                
            if total_processed % 10000 == 0:
                print(f"Processed {total_processed:,} records... Time: {time.time() - start_time:.1f}s")
                
    print(f"Extraction Complete! Total Records: {total_processed:,}")

# 6. RUN THE PIPELINE
if __name__ == "__main__":
    import os
    
    input_file = "entropy_narratives.txt"
    output_file = "extracted_graph_nodes.jsonl"
    
    # 1. Check if the file exists and is not empty
    if not os.path.exists(input_file):
        print(f"ERROR: '{input_file}' is missing. Run the generator script first.")
    elif os.path.getsize(input_file) == 0:
        print(f"ERROR: '{input_file}' is completely empty (0 bytes). Re-run the generator script.")
    else:
        # 2. Run the extraction
        print(f"Found input file. Size: {os.path.getsize(input_file)} bytes.")
        run_extraction_pipeline(input_file, output_file)
        
        # 3. Verify output
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"SUCCESS: Data successfully written to {output_file}")
            print("Run 'head extracted_graph_nodes.jsonl' in your terminal to see the first few lines.")
        else:
            print("FAILED: Extraction ran, but no data was written.")