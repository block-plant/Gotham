"""
Real-world Police FIR Data Extractor for GNN Criminal Linkage.
Extracts rich multi-modal entities, modus operandi, legal statutes, spatial hierarchies,
gang demographic profiles, and synthesized investigative narratives from real FIR records.
"""
import csv
import json
import time
import os
import sys
import re
import argparse

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Landmark pattern matching for Place of Offence
LANDMARK_PATTERNS = [
    ("LANDMARK_BUS_STAND", re.compile(r"BUS\s*STAND|BUS\s*STOP|KSRTC|BMTC", re.I)),
    ("LANDMARK_HIGHWAY", re.compile(r"HIGHWAY|NH[\-\s]?\d+|SH[\-\s]?\d+|RING\s*ROAD|EXPRESSWAY", re.I)),
    ("LANDMARK_TEMPLE", re.compile(r"TEMPLE|TEMPEL|MANDIR|MASJID|MOSQUE|CHURCH|DURGA|MATHA", re.I)),
    ("LANDMARK_MARKET", re.compile(r"MARKET|BAZAR|BAZAAR|APMC|COMPLEX|MALL|SHOPPING", re.I)),
    ("LANDMARK_JEWELRY", re.compile(r"JEWELL|JEWELLERY|JEWELRY|GOLD|SILVER|PAWN", re.I)),
    ("LANDMARK_BANK_ATM", re.compile(r"BANK|ATM|CASH|FINANCE|SBI|HDFC|ICICI|CANARA", re.I)),
    ("LANDMARK_PETROL_PUMP", re.compile(r"PETROL|PUMP|DIESEL|HPCL|BPCL|IOCL|INDIAN\s*OIL", re.I)),
    ("LANDMARK_RESIDENTIAL", re.compile(r"HOUSE|RESIDEN|HOME|FLAT|APARTMENT|COLONY|LAYOUT|NAGAR", re.I)),
    ("LANDMARK_COMMERCIAL", re.compile(r"SHOP|COMMERCIAL|FACTORY|INDUSTRIAL|OFFICE|WAREHOUSE|GODOWN", re.I)),
    ("LANDMARK_RAILWAY", re.compile(r"RAILWAY|STATION|TRACK|TRAIN|PLATFORM", re.I)),
    ("LANDMARK_HOSPITAL", re.compile(r"HOSPITAL|CLINIC|HEALTH|NURSING", re.I)),
    ("LANDMARK_BAR_HOTEL", re.compile(r"BAR|LODGE|HOTEL|RESTO|RESTAURANT|DHABA", re.I)),
]

# Legal Act / Section Normalizer
ACT_PATTERNS = [
    ("ACT_IPC_", re.compile(r"IPC\s*(?:1860)?\s*(?:U/s:?|SEC(?:TION)?:?)?\s*([0-9]{2,3}[A-Z]?(?:\s*,\s*[0-9]{2,3}[A-Z]?)*)", re.I)),
    ("ACT_BNS_", re.compile(r"BNS\s*(?:2023)?\s*(?:U/s:?|SEC(?:TION)?:?)?\s*([0-9]{2,3}[A-Z]?(?:\s*,\s*[0-9]{2,3}[A-Z]?)*)", re.I)),
    ("ACT_POCSO_", re.compile(r"POCSO|PROTECTION OF CHILDREN.*?(?:U/s:?|SEC(?:TION)?:?)?\s*([0-9]{1,2}[A-Z]?)", re.I)),
    ("ACT_KP_", re.compile(r"KARNATAKA POLICE ACT.*?(?:U/s:?|SEC(?:TION)?:?)?\s*([0-9]{1,3}(?:\([0-9A-Z]+\))?)", re.I)),
    ("ACT_NDPS_", re.compile(r"NDPS|NARCOTIC.*?(?:U/s:?|SEC(?:TION)?:?)?\s*([0-9]{1,3}[A-Z]?)", re.I)),
    ("ACT_IT_", re.compile(r"INFORMATION TECHNOLOGY|IT ACT.*?(?:U/s:?|SEC(?:TION)?:?)?\s*([0-9]{2,3}[A-Z]?)", re.I)),
    ("ACT_ARMS_", re.compile(r"ARMS ACT.*?(?:U/s:?|SEC(?:TION)?:?)?\s*([0-9]{1,3}[A-Z]?)", re.I)),
    ("ACT_EXCISE_", re.compile(r"EXCISE ACT.*?(?:U/s:?|SEC(?:TION)?:?)?\s*([0-9]{1,3}[A-Z]?)", re.I)),
    ("ACT_MV_", re.compile(r"MOTOR VEHICLE|IMV ACT.*?(?:U/s:?|SEC(?:TION)?:?)?\s*([0-9]{1,3}[A-Z]?)", re.I)),
]

def clean_string(s):
    if not s or s.strip() == "": return None
    return s.strip().upper()

def extract_landmarks(place_text):
    if not place_text: return []
    landmarks = []
    for lm_id, pat in LANDMARK_PATTERNS:
        if pat.search(place_text):
            landmarks.append(lm_id)
    return landmarks

def normalize_act_sections(raw_act):
    if not raw_act: return []
    sections = []
    
    # Try pattern matching
    matched = False
    for prefix, pat in ACT_PATTERNS:
        for m in pat.finditer(raw_act):
            matched = True
            sec_str = m.group(1) if m.groups() else ""
            if sec_str:
                for s in re.split(r"[,\s/]+", sec_str):
                    s_clean = s.strip().upper()
                    if s_clean and len(s_clean) <= 10:
                        sections.append(f"{prefix}{s_clean}")
            else:
                sections.append(prefix.rstrip("_"))
                
    if not matched:
        # Fallback generic cleaning
        words = re.findall(r"(?:IPC|BNS|NDPS|POCSO|KP)[\-\s]?[0-9]{2,3}[A-Z]?", raw_act, re.I)
        for w in words:
            clean_w = re.sub(r"\s+", "_", w.upper())
            sections.append(f"ACT_{clean_w}")
            
    return list(dict.fromkeys(sections))

def parse_distance_km(val):
    if not val: return 0.0
    val_str = str(val).strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:KM)?", val_str, re.I)
    if match:
        try: return float(match.group(1))
        except: return 0.0
    try: return float(val_str)
    except: return 0.0

def get_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == "": return default
        return float(val)
    except: return default

def process_kaggle_csv(input_csvs=["data/kaggle_fir_data.csv"], output_jsonl="data/extracted_graph_nodes.jsonl", max_rows=None):
    if input_csvs is None:
        input_csvs = ["data/kaggle_fir_data.csv"]
        if os.path.exists(os.path.join("data", "injected_syndicates.csv")):
            input_csvs.append(os.path.join("data", "injected_syndicates.csv"))
    elif isinstance(input_csvs, str):
        input_csvs = [input_csvs]

    print(f"[*] Starting Detective Multi-Source Extraction to {output_jsonl}...")
    print(f"    Source CSVs: {input_csvs}")
    start_time = time.time()
    total_processed = 0
    heinous_count = 0
    multi_accused_count = 0

    with open(output_jsonl, 'w', encoding='utf-8') as f_out:
        for input_csv in input_csvs:
            if not os.path.exists(input_csv):
                print(f"Warning: File not found: {input_csv}. Skipping.")
                continue

            print(f"  --> Ingesting records from: {input_csv}")
            file_processed = 0
            is_injected = "injected" in input_csv.lower()
            
            with open(input_csv, 'r', encoding='utf-8', errors='replace') as f_in:
                reader = csv.DictReader(f_in)
                for row in reader:
                    if not is_injected and max_rows and file_processed >= max_rows:
                        break

                    fir_id = f"FIR_{total_processed}"

                    district = clean_string(row.get("District_Name"))
                    unit_name = clean_string(row.get("UnitName"))
                    crime_group = clean_string(row.get("CrimeGroup_Name"))
                    crime_head = clean_string(row.get("CrimeHead_Name"))
                    raw_act = row.get("ActSection", "")
                    io_name = clean_string(row.get("IOName"))
                    internal_io = clean_string(row.get("Internal_IO"))
                    place_of_offence = row.get("Place of Offence", "").strip()
                    beat_name = clean_string(row.get("Beat_Name"))
                    village_name = clean_string(row.get("Village_Area_Name"))
                    fir_type = clean_string(row.get("FIR Type", "NON HEINOUS"))
                    fir_stage = clean_string(row.get("FIR_Stage", "UNKNOWN"))
                    complaint_mode = clean_string(row.get("Complaint_Mode", "UNKNOWN"))
                    
                    # Numeric fields
                    accused_count = int(get_float(row.get("Accused Count"), 1.0))
                    if accused_count <= 0: accused_count = 1
                    arrested_count = int(get_float(row.get("Arrested Count\tNo.") or row.get("Arrested Count No."), 0.0))
                    chargesheeted_count = int(get_float(row.get("Accused_ChargeSheeted Count"), 0.0))
                    conviction_count = int(get_float(row.get("Conviction Count"), 0.0))
                    victim_count = int(get_float(row.get("VICTIM COUNT"), 0.0))
                    offence_duration = get_float(row.get("Offence_Duration"), 0.0)
                    distance_from_ps = parse_distance_km(row.get("Distance from PS"))
                    
                    fir_year = int(get_float(row.get("FIR_YEAR"), 2020))
                    fir_month = int(get_float(row.get("FIR_MONTH"), 1))
                    fir_day = int(get_float(row.get("FIR_Day"), 1))
                    
                    is_heinous = 1.0 if "HEINOUS" in (fir_type or "") and "NON" not in (fir_type or "") else 0.0
                    if is_heinous: heinous_count += 1
                    if accused_count >= 2: multi_accused_count += 1

                    # Gang Scale Signature
                    if accused_count == 1:
                        gang_scale = "GANG_SOLO"
                    elif accused_count == 2:
                        gang_scale = "GANG_DUO_2"
                    elif 3 <= accused_count <= 5:
                        gang_scale = "GANG_GROUP_3_5"
                    else:
                        gang_scale = "GANG_SYNDICATE_6PLUS"

                    # Parse Act Sections and Landmarks
                    act_sections = normalize_act_sections(raw_act)
                    landmarks = extract_landmarks(place_of_offence)

                    entities = {
                        "districts": [f"DIST_{district}"] if district and district not in ["NULL", "NA"] else [],
                        "units": [f"UNIT_{unit_name}"] if unit_name and unit_name not in ["NULL", "NA"] else [],
                        "crime_groups": [f"CG_{crime_group}"] if crime_group and crime_group not in ["NULL", "NA"] else [],
                        "crime_heads": [f"MO_{crime_head}"] if crime_head and crime_head not in ["NULL", "NA"] else [],
                        "act_sections": act_sections,
                        "ios": [f"IO_{io_name}"] if io_name and io_name not in ["NULL", "NA"] else [],
                        "beats": [f"BEAT_{beat_name}"] if beat_name and beat_name not in ["NULL", "NA"] else [],
                        "areas": [f"AREA_{village_name}"] if village_name and village_name not in ["NULL", "NA"] else [],
                        "landmarks": landmarks,
                        "gang_scales": [gang_scale],
                    }
                    if internal_io and internal_io not in ["NULL", "NA", "0"]:
                        entities["ios"].append(f"IO_{internal_io}")

                    # Clean and deduplicate entities
                    entities = {k: list(dict.fromkeys(v)) for k, v in entities.items() if v}

                    numeric_features = {
                        "offence_duration": offence_duration,
                        "distance_from_ps": distance_from_ps,
                        "victim_count": victim_count,
                        "accused_count": accused_count,
                        "arrested_count": arrested_count,
                        "chargesheeted_count": chargesheeted_count,
                        "conviction_count": conviction_count,
                        "is_heinous": is_heinous,
                        "fir_year": fir_year,
                        "fir_month": fir_month,
                        "fir_day": fir_day,
                    }

                    # Synthesize Rich Investigative Case Summary for NLP Embedding
                    act_summary = ", ".join(act_sections[:3]) if act_sections else "General Penal Provisions"
                    place_summary = place_of_offence if place_of_offence else (village_name or district or "Unspecified Location")
                    narrative = (
                        f"[CRIME: {crime_group or 'UNKNOWN'}] [MO: {crime_head or 'GENERAL'}] "
                        f"[STATUTES: {act_summary}] "
                        f"[LOCATION: {place_summary}, Beat: {beat_name or 'N/A'}, Station: {unit_name or 'N/A'}, District: {district or 'N/A'}] "
                        f"[DEMOGRAPHICS: Accused: {accused_count}, Arrested: {arrested_count}, Chargesheeted: {chargesheeted_count}, Victims: {victim_count}, GangProfile: {gang_scale}] "
                        f"[STAGE: {fir_stage or 'PENDING'}, Type: {fir_type or 'NON HEINOUS'}, Mode: {complaint_mode or 'WRITTEN'}]"
                    )

                    record = {
                        "fir_id": fir_id,
                        "entities": entities,
                        "numeric_features": numeric_features,
                        "narrative": narrative,
                        "interactions": []
                    }

                    f_out.write(json.dumps(record) + "\n")
                    total_processed += 1
                    file_processed += 1
                    if total_processed % 50000 == 0:
                        print(f"    Processed {total_processed:,} records... ({time.time() - start_time:.1f}s)")

    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print(f"✓ Detective Extraction Complete in {elapsed:.2f}s!")
    print(f"  Total Records Processed: {total_processed:,}")
    print(f"  Multi-Accused Gang Cases: {multi_accused_count:,} ({multi_accused_count/max(1, total_processed)*100:.1f}%)")
    print(f"  Heinous Crime Cases: {heinous_count:,}")
    print(f"  Output saved to: {output_jsonl}")
    print("="*60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract real FIR entities and injected syndicates for GNN linkage.")
    parser.add_argument("--inputs", nargs="+", default=None, help="Input CSV file path(s)")
    parser.add_argument("--output", default="data/extracted_graph_nodes.jsonl", help="Output JSONL file path")
    parser.add_argument("--max-rows", type=int, default=None, help="Optional row limit for prototyping")
    args = parser.parse_args()

    process_kaggle_csv(input_csvs=args.inputs, output_jsonl=args.output, max_rows=args.max_rows)
