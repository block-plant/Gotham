"""
Dedicated Stealth Criminal Syndicate & Invisible Gang Generator.
Creates realistic, complex multi-station criminal chains in a separate file (injected_syndicates.csv),
keeping kaggle_fir_data.csv 100% clean and uncorrupted.

Key Features of Injected Invisible Syndicates:
1. Zero Direct Shared Arrests between subgroup leaders (humans cannot spot them via simple co-arrest lookups).
2. Subtle Multi-Hop Investigative Connectors:
   - Shared cross-station transit corridors (e.g. National Highways NH-44 / NH-48).
   - Rare specialized tool signatures (e.g. Titanium gas cutters [Serial: W_TITANIUM_CUTTER_99]).
   - Shared hawala/burner routing tags (e.g. [Tag: PH_HAWALA_7788]).
   - Specific unique modus operandi timing (e.g. 03:30 AM night jewelry heist).
"""
import os
import sys
import csv
import json
import random

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

OUTPUT_CSV = os.path.join("data_processing", "injected_syndicates.csv")
GROUND_TRUTH_JSON = os.path.join("graph_tensors", "ground_truth_invisible_links.json")

# 5 Major Strategic Invisible Syndicates
BIG_SYNDICATES = [
    {
        "name": "THE_SHADOW_CORRIDOR_DACOITY_CARTEL",
        "description": "Cross-district armed highway dacoity syndicate along NH-44 corridor using titanium gas cutters",
        "crime_group": "DACOITY",
        "crime_head": "PREPARATION AND ASSEMBLY FOR DACOITY",
        "act_sections": "IPC 1860 U/s: 395,397 ARMS ACT 1959 U/s: 25,27",
        "fir_type": "Heinous",
        "locations": [
            ("Bengaluru City", "Hebbal PS", "RURAL BEAT NO 4", "KEMPEGOWDA HIGHWAY FLYOVER NEAR TOLL", "WEST FROM PS 14 KM"),
            ("Tumakuru", "Tumakuru Rural PS", "HIGHWAY BEAT 2", "NH-44 INDUSTRIAL CORRIDOR GAS GODOWN", "NORTH FROM PS 18 KM"),
            ("Belagavi Dist", "Chikodi PS", "BORDER BEAT 7", "STATE BORDER TRUCK TERMINAL NH-48", "WEST FROM PS 22 KM"),
            ("Bengaluru Dist", "Hosakote PS", "HIGHWAY BEAT 1", "NH-44 TOLL PLAZA SERVICE ROAD NEAR PETROL PUMP", "EAST FROM PS 16 KM"),
            ("Ballari", "Cowl Bazar PS", "MINING BEAT 3", "BALLARI BYPASS MINING TRUCK JUNCTION", "SOUTH FROM PS 12 KM"),
        ],
        "sub_teams": [
            {"leader": "Vikram_Malhotra", "partner": "Ravi_Kashyap", "accused": 4, "arrested": 2},
            {"leader": "Devendra_Rao", "partner": "Suresh_Nair", "accused": 3, "arrested": 1},
            {"leader": "Irfan_Pasha", "partner": "Kabir_Khan", "accused": 5, "arrested": 3},
            {"leader": "Anand_Shetty", "partner": "Manjunath_Gowda", "accused": 4, "arrested": 2},
            {"leader": "Sunil_Verma", "partner": "Rajesh_Patel", "accused": 3, "arrested": 1},
        ],
        "signature": "[Serial: W_TITANIUM_CUTTER_99] White SUV getaway vehicle without plates"
    },
    {
        "name": "PHANTOM_CYBER_HAWALA_NETWORK",
        "description": "Cross-station banking & cyber OTP phishing syndicate routing through shared crypto/hawala accounts",
        "crime_group": " CYBER CRIME",
        "crime_head": "Information Technology Act 2000, 2009",
        "act_sections": "INFORMATION TECHNOLOGY ACT 2000 U/s: 66C,66D IPC 1860 U/s: 420,120B",
        "fir_type": "Non Heinous",
        "locations": [
            ("Bengaluru City", "Cyber Crime PS", "TECH BEAT NO 1", "MANYATA TECH PARK CYBER CAFE", "EAST FROM PS 5 KM"),
            ("Bengaluru City", "Indiranagar PS", "COMMERCIAL BEAT 3", "100 FEET ROAD INDIRANAGAR ATM KIOSK", "WEST FROM PS 3 KM"),
            ("Bengaluru City", "Whitefield PS", "ITPL BEAT 5", "ITPL MAIN ROAD NEAR METRO STATION", "SOUTH FROM PS 4 KM"),
            ("Mysuru Dist", "V V Puram PS", "URBAN BEAT 2", "GOKULAM 3RD STAGE INTERNET CENTER", "NORTH FROM PS 6 KM"),
        ],
        "sub_teams": [
            {"leader": "Aakash_Srivastava", "partner": "Rohan_Mehta", "accused": 3, "arrested": 1},
            {"leader": "Karan_Singhania", "partner": "Deepak_Joshi", "accused": 4, "arrested": 2},
            {"leader": "Sameer_Qureshi", "partner": "Tariq_Aziz", "accused": 2, "arrested": 1},
            {"leader": "Prashant_Deshmukh", "partner": "Alok_Pandey", "accused": 3, "arrested": 0},
        ],
        "signature": "[Tag: PH_HAWALA_7788] Synthetic mule SIM cards and instant Telegram USDT laundering"
    },
    {
        "name": "GHOST_RIDER_SNATCHING_CELL",
        "description": "High-speed motorcycle chain snatching duo rotation across residential beats in Bengaluru and Mysuru",
        "crime_group": "ROBBERY",
        "crime_head": "Chain Snatching",
        "act_sections": "IPC 1860 U/s: 392,34",
        "fir_type": "Non Heinous",
        "locations": [
            ("Bengaluru City", "Koramangala PS", "RURAL BEAT NO 13", "KORAMANGALA 4TH BLOCK BUS STAND CORNER", "EAST FROM PS 3 KM"),
            ("Bengaluru City", "Jayanagar PS", "RESIDENTIAL BEAT 4", "4TH BLOCK JAYANAGAR SHOPPING COMPLEX ROAD", "SOUTH FROM PS 2 KM"),
            ("Mysuru Dist", "Nazarbad PS", "PALACE BEAT 1", "HARDINGE CIRCLE NEAR BUS STOP", "WEST FROM PS 4 KM"),
            ("Bengaluru Dist", "Nelamangala PS", "TOWN BEAT 2", "NELAMANGALA TOWN TEMPLE ENTRANCE ROAD", "NORTH FROM PS 5 KM"),
        ],
        "sub_teams": [
            {"leader": "Suraj_Thakur", "partner": "Manoj_Yadav", "accused": 2, "arrested": 1},
            {"leader": "Kishore_Reddy", "partner": "Dinesh_Kumar", "accused": 2, "arrested": 1},
            {"leader": "Arif_Siddiqui", "partner": "Salman_Baig", "accused": 2, "arrested": 0},
            {"leader": "Naveen_Poojary", "partner": "Girish_Acharya", "accused": 2, "arrested": 1},
        ],
        "signature": "[Vehicle: PULSAR-220-BLACK] Modified black sports bike without rear mirror"
    },
    {
        "name": "NIGHT_VIPER_TEMPLE_BURGLARY",
        "description": "Night antique idol and jewelry burglary syndicate targeting rural temples across northern Karnataka",
        "crime_group": "BURGLARY - NIGHT",
        "crime_head": "Temple Theft",
        "act_sections": "IPC 1860 U/s: 457,380",
        "fir_type": "Heinous",
        "locations": [
            ("Bagalkot", "Amengad PS", "RURAL BEAT NO 6", "RAKKASAGI MOUNESHWAR TEMPLE BACK GATE", "WEST FROM PS 12 KM"),
            ("Ballari", "Siruguppa PS", "RIVER BEAT 4", "TUNGABHADRA RIVER SHORE ANCIENT SHIVA TEMPLE", "EAST FROM PS 15 KM"),
            ("Belagavi Dist", "Gokak PS", "FALLS BEAT 2", "GOKAK RURAL ANJANEYA TEMPLE SANCTUM", "NORTH FROM PS 18 KM"),
            ("Bagalkot", "Badami PS", "CAVE BEAT 1", "BADAMI HERITAGE TEMPLE COMPOUND", "SOUTH FROM PS 8 KM"),
        ],
        "sub_teams": [
            {"leader": "Shivaji_Gounder", "partner": "Dharma_Lingam", "accused": 3, "arrested": 1},
            {"leader": "Basavaraj_Kattimani", "partner": "Yellappa_Naik", "accused": 4, "arrested": 2},
            {"leader": "Someshwar_Babu", "partner": "Rangaswamy_M", "accused": 3, "arrested": 1},
            {"leader": "Shankar_Doddamani", "partner": "Mallikarjun_H", "accused": 3, "arrested": 0},
        ],
        "signature": "[Tool: HYDRAULIC_BOLT_CUTTER] Antique brass and gold deity ornaments targeted"
    },
    {
        "name": "UNDERGROUND_EXTORTION_NETWORK",
        "description": "Commercial builder and trader extortion syndicate issuing threats across commercial hubs",
        "crime_group": "EXTORTION",
        "crime_head": "For Ransom",
        "act_sections": "IPC 1860 U/s: 384,387,506",
        "fir_type": "Heinous",
        "locations": [
            ("Bengaluru City", "City Market PS", "MARKET BEAT 1", "KR MARKET COMMERCIAL WHOLESALE COMPLEX", "WEST FROM PS 1 KM"),
            ("Bengaluru City", "Commercial Street PS", "BAZAR BEAT 2", "COMMERCIAL STREET JEWELRY ARCADE", "EAST FROM PS 2 KM"),
            ("Tumakuru", "Tumakuru Town PS", "TRADER BEAT 3", "APMC YARD WHOLESALE GRAIN MARKET", "NORTH FROM PS 4 KM"),
            ("Belagavi Dist", "Belagavi City PS", "INDUSTRIAL BEAT 5", "UDYAMBAG INDUSTRIAL ESTATE MAIN GATE", "SOUTH FROM PS 6 KM"),
        ],
        "sub_teams": [
            {"leader": "Don_Rajan_Kolar", "partner": "Sharath_Bangalore", "accused": 4, "arrested": 2},
            {"leader": "Javed_Don_Bhatkal", "partner": "Imtiaz_Babu", "accused": 3, "arrested": 1},
            {"leader": "Ganesh_Appa_Hubli", "partner": "Vithal_Marathe", "accused": 4, "arrested": 2},
            {"leader": "Ramesh_Anna_Bellary", "partner": "Thimmappa_G", "accused": 3, "arrested": 0},
        ],
        "signature": "[VoIP: VIRTUAL_NUMBER_ROUTING] International VoIP threat calls demanding crypto protection"
    }
]

CSV_HEADER = [
    'District_Name', 'UnitName', 'FIR_YEAR', 'FIR_MONTH', 'Offence_Duration', 'FIR_Day',
    'FIR Type', 'FIR_Stage', 'Complaint_Mode', 'CrimeGroup_Name', 'CrimeHead_Name',
    'Latitude', 'Longitude', 'ActSection', 'IOName', 'KGID', 'Internal_IO',
    'Place of Offence', 'Distance from PS', 'Beat_Name', 'Village_Area_Name',
    'Male', 'Female', 'Boy', 'Girl', 'Age 0', 'VICTIM COUNT', 'Accused Count',
    'Arrested Male', 'Arrested Female', 'Arrested Count\tNo.', 'Accused_ChargeSheeted Count',
    'Conviction Count', 'Unit_ID'
]

def generate_injected_syndicates(output_csv=OUTPUT_CSV, ground_truth_json=GROUND_TRUTH_JSON):
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    os.makedirs(os.path.dirname(ground_truth_json), exist_ok=True)

    print(f"[*] Generating Stealth Invisible Syndicates to separate file: {output_csv}...")
    
    rows_written = 0
    ground_truth_syndicates = []
    
    with open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=CSV_HEADER)
        writer.writeheader()

        fir_counter = 8800000 # High unique KGID block to avoid any collision
        
        # 1. Inject Big Strategic Syndicates
        for syn in BIG_SYNDICATES:
            syn_fir_ids = []
            syn_cases_info = []

            for idx, (loc, team) in enumerate(zip(syn["locations"], syn["sub_teams"])):
                fir_counter += 1
                fir_kgid = str(fir_counter)
                fir_id = f"FIR-{fir_kgid}"
                syn_fir_ids.append(fir_id)

                dist_name, unit_name, beat_name, place_text, dist_ps = loc
                place_with_sig = f"{place_text} ({syn['signature']})"

                row_dict = {
                    'District_Name': dist_name,
                    'UnitName': unit_name,
                    'FIR_YEAR': 2021,
                    'FIR_MONTH': random.randint(1, 12),
                    'Offence_Duration': random.randint(1, 12),
                    'FIR_Day': f"{random.randint(1, 28):02d}",
                    'FIR Type': syn["fir_type"],
                    'FIR_Stage': "Chargesheeted" if team["arrested"] > 0 else "Under Investigation",
                    'Complaint_Mode': "Written",
                    'CrimeGroup_Name': syn["crime_group"],
                    'CrimeHead_Name': syn["crime_head"],
                    'Latitude': '0.0',
                    'Longitude': '0.0',
                    'ActSection': syn["act_sections"],
                    'IOName': f"INSPECTOR_{dist_name.upper().replace(' ', '_')}_{idx+1}",
                    'KGID': fir_kgid,
                    'Internal_IO': f"IO_INJ_{idx+1}",
                    'Place of Offence': place_with_sig,
                    'Distance from PS': dist_ps,
                    'Beat_Name': beat_name,
                    'Village_Area_Name': f"AREA_{unit_name.upper().replace(' ', '_')}",
                    'Male': 1,
                    'Female': 0,
                    'Boy': 0,
                    'Girl': 0,
                    'Age 0': 0,
                    'VICTIM COUNT': 1,
                    'Accused Count': team["accused"],
                    'Arrested Male': team["arrested"],
                    'Arrested Female': 0,
                    'Arrested Count\tNo.': team["arrested"],
                    'Accused_ChargeSheeted Count': team["arrested"],
                    'Conviction Count': 0,
                    'Unit_ID': 9900 + idx
                }

                writer.writerow(row_dict)
                rows_written += 1
                
                syn_cases_info.append({
                    "fir_id": fir_id,
                    "district": dist_name,
                    "unit": unit_name,
                    "beat": beat_name,
                    "leader": team["leader"],
                    "partner": team["partner"],
                    "accused_count": team["accused"],
                    "arrested_count": team["arrested"],
                })

            # Create Ground Truth Invisible Pairs (all pairwise cases in this syndicate)
            invisible_pairs = []
            for i in range(len(syn_fir_ids)):
                for j in range(i + 1, len(syn_fir_ids)):
                    invisible_pairs.append([syn_fir_ids[i], syn_fir_ids[j]])

            ground_truth_syndicates.append({
                "syndicate_name": syn["name"],
                "description": syn["description"],
                "crime_group": syn["crime_group"],
                "crime_head": syn["crime_head"],
                "signature": syn["signature"],
                "total_cases": len(syn_fir_ids),
                "case_ids": syn_fir_ids,
                "cases_info": syn_cases_info,
                "invisible_link_pairs": invisible_pairs,
            })

        # 2. Inject 20 Localized Stealth Cells (spanning 3-4 cross-beat cases each)
        for c_idx in range(1, 21):
            cell_name = f"STEALTH_LOCAL_CELL_{c_idx:02d}"
            cell_fir_ids = []
            cell_cases_info = []
            
            base_dist = random.choice(["Bengaluru City", "Mysuru Dist", "Tumakuru", "Belagavi Dist", "Ballari"])
            crime_type = random.choice([
                ("THEFT", "Of Automobiles - Of Two Wheelers", "IPC 1860 U/s: 379"),
                ("BURGLARY - NIGHT", "At Residential Premises", "IPC 1860 U/s: 457,380"),
                ("CHEATING", "Cheating", "IPC 1860 U/s: 420"),
                ("KARNATAKA POLICE ACT 1963", "Gambling - Matka (78 Class C)", "KARNATAKA POLICE ACT 1963 U/s: 78(3)")
            ])
            cell_cg, cell_mo, cell_act = crime_type

            for step in range(3):
                fir_counter += 1
                fir_kgid = str(fir_counter)
                fir_id = f"FIR-{fir_kgid}"
                cell_fir_ids.append(fir_id)

                row_dict = {
                    'District_Name': base_dist,
                    'UnitName': f"CELL_UNIT_{c_idx}_{step+1}",
                    'FIR_YEAR': 2022,
                    'FIR_MONTH': random.randint(1, 12),
                    'Offence_Duration': 2,
                    'FIR_Day': f"{random.randint(1, 28):02d}",
                    'FIR Type': "Non Heinous",
                    'FIR_Stage': "Under Investigation",
                    'Complaint_Mode': "Written",
                    'CrimeGroup_Name': cell_cg,
                    'CrimeHead_Name': cell_mo,
                    'Latitude': '0.0',
                    'Longitude': '0.0',
                    'ActSection': cell_act,
                    'IOName': f"IO_CELL_{c_idx}",
                    'KGID': fir_kgid,
                    'Internal_IO': f"IO_INTERNAL_{c_idx}",
                    'Place of Offence': f"LOCAL SECTOR-{step+10} NEAR RESIDENTIAL CORNER (CELL_TAG_{c_idx})",
                    'Distance from PS': f"WEST {step+2} KM",
                    'Beat_Name': f"CELL_BEAT_{c_idx}_{step+1}",
                    'Village_Area_Name': f"CELL_AREA_{c_idx}",
                    'Male': 1,
                    'Female': 0,
                    'Boy': 0,
                    'Girl': 0,
                    'Age 0': 0,
                    'VICTIM COUNT': 1,
                    'Accused Count': 2,
                    'Arrested Male': 1 if step == 0 else 0,
                    'Arrested Female': 0,
                    'Arrested Count\tNo.': 1 if step == 0 else 0,
                    'Accused_ChargeSheeted Count': 0,
                    'Conviction Count': 0,
                    'Unit_ID': 8800 + c_idx
                }
                writer.writerow(row_dict)
                rows_written += 1
                cell_cases_info.append({"fir_id": fir_id, "district": base_dist})

            cell_pairs = []
            for i in range(len(cell_fir_ids)):
                for j in range(i + 1, len(cell_fir_ids)):
                    cell_pairs.append([cell_fir_ids[i], cell_fir_ids[j]])

            ground_truth_syndicates.append({
                "syndicate_name": cell_name,
                "description": f"Localized stealth cell operating across 3 beats in {base_dist}",
                "crime_group": cell_cg,
                "crime_head": cell_mo,
                "signature": f"CELL_TAG_{c_idx}",
                "total_cases": len(cell_fir_ids),
                "case_ids": cell_fir_ids,
                "cases_info": cell_cases_info,
                "invisible_link_pairs": cell_pairs,
            })

    # Save Ground Truth Benchmark JSON
    with open(ground_truth_json, "w", encoding="utf-8") as f_gt:
        json.dump({
            "total_syndicates": len(ground_truth_syndicates),
            "total_injected_records": rows_written,
            "syndicates": ground_truth_syndicates
        }, f_gt, indent=2)

    print(f"\n✓ Successfully generated {rows_written} stealth syndicate records in: {output_csv}")
    print(f"✓ Saved ground-truth benchmark pairs in: {ground_truth_json}")
    print(f"  - 5 Major Multi-District Syndicates ({sum(len(s['case_ids']) for s in ground_truth_syndicates[:5])} cases)")
    print(f"  - 20 Localized Stealth Cells ({sum(len(s['case_ids']) for s in ground_truth_syndicates[5:])} cases)")
    print(f"  - Original 'kaggle_fir_data.csv' remains 100% UNTOUCHED.")

if __name__ == "__main__":
    generate_injected_syndicates()
