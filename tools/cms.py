"""Criminal data management: ingest a FIR, auto-place it, expand every link.

The operator never chooses a slot. Overlapping IDs, phones, vehicles, serials,
hotspots and statutes decide the merge. Then the system lists every person
tied to that identity — including links clerks usually never type twice.
"""
import argparse
import json
import os
from collections import defaultdict

from tools.forensic import CHAIN_LAWS, extract_fields

INDEX_PATH = os.path.join("graph_tensors", "cms_index.json")
LOG_PATH = os.path.join("graph_tensors", "cms_ingest_log.jsonl")


def _empty_index():
    return {
        "records": [],
        "people": {},
        "name_to_ids": {},
        "phone_to_ids": {},
        "tag_to_ids": {},
        "vehicle_to_ids": {},
        "weapon_to_ids": {},
        "location_to_ids": {},
        "law_to_ids": {},
        "clusters": {},
    }


def _add(mapping, key, value):
    if not key:
        return
    bucket = mapping.setdefault(key, [])
    if value not in bucket:
        bucket.append(value)


def _union_find():
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    return find, union


def build_index(narrative_path="entropy_narratives.txt", out_path=INDEX_PATH):
    index = _empty_index()
    if not os.path.exists(narrative_path):
        raise FileNotFoundError(f"Missing {narrative_path}")

    with open(narrative_path, "r", encoding="utf-8") as handle:
        for line_idx, line in enumerate(handle):
            text = line.strip()
            if not text:
                continue
            fields = extract_fields(text)
            fir_id = f"FIR-{line_idx:06d}"
            person_id = fields["person_ids"][0] if fields["person_ids"] else f"UNID_{line_idx:06d}"
            name = fields["aliases"].get(person_id) or (
                fields["names"][0] if fields["names"] else "UNKNOWN"
            )

            index["records"].append(
                {
                    "fir_id": fir_id,
                    "person_id": person_id,
                    "name": name,
                    "is_chain": fields["is_chain"],
                }
            )

            person = index["people"].setdefault(
                person_id,
                {
                    "person_id": person_id,
                    "name": name,
                    "firs": [],
                    "phones": [],
                    "phone_tags": [],
                    "vehicles": [],
                    "weapons": [],
                    "laws": [],
                    "locations": [],
                    "chain_hits": 0,
                },
            )
            person["name"] = name
            person["firs"].append(fir_id)
            if fields["is_chain"]:
                person["chain_hits"] += 1

            for phone in fields["phones"]:
                _add(person, "phones", phone)
                _add(index["phone_to_ids"], phone, person_id)
            for tag in fields["phone_tags"]:
                _add(person, "phone_tags", tag)
                _add(index["tag_to_ids"], tag, person_id)
            for vehicle in fields["vehicles"]:
                _add(person, "vehicles", vehicle)
                _add(index["vehicle_to_ids"], vehicle, person_id)
            for weapon in fields["weapons"]:
                _add(person, "weapons", weapon)
                _add(index["weapon_to_ids"], weapon, person_id)
            for loc in fields["locations"]:
                _add(person, "locations", loc)
                _add(index["location_to_ids"], loc.lower(), person_id)
            for law in fields["laws"]:
                _add(person, "laws", law)
                _add(index["law_to_ids"], law, person_id)
            _add(index["name_to_ids"], name.lower(), person_id)

    find, union = _union_find()
    for mapping in (
        index["phone_to_ids"],
        index["tag_to_ids"],
        index["vehicle_to_ids"],
        index["weapon_to_ids"],
    ):
        for ids in mapping.values():
            for other in ids[1:]:
                union(ids[0], other)

    clusters = defaultdict(list)
    for person_id in index["people"]:
        clusters[find(person_id)].append(person_id)
    index["clusters"] = {
        root: members for root, members in clusters.items() if len(members) > 1
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(index, handle)
    print(
        f"CMS index: {len(index['records']):,} FIRs | "
        f"{len(index['people']):,} people | "
        f"{len(index['clusters']):,} hidden clusters -> {out_path}"
    )
    return index


def load_index(path=INDEX_PATH):
    if not os.path.exists(path):
        return build_index(out_path=path)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _score_person(person, fields):
    score = 0
    reasons = []
    if person["person_id"] in fields["person_ids"]:
        score += 100
        reasons.append("same cryptographic person ID")
    if set(person.get("phones", [])) & set(fields["phones"]):
        score += 80
        reasons.append("shared phone number")
    if set(person.get("phone_tags", [])) & set(fields["phone_tags"]):
        score += 80
        reasons.append("shared PH_ tag (usually ignored while typing the FIR)")
    if set(person.get("vehicles", [])) & set(fields["vehicles"]):
        score += 80
        reasons.append("shared vehicle")
    if set(person.get("weapons", [])) & set(fields["weapons"]):
        score += 70
        reasons.append("shared weapon serial")
    if person["name"].lower() in {name.lower() for name in fields["names"]}:
        score += 25
        reasons.append("same display name")
    loc_hit = {loc.lower() for loc in person.get("locations", [])} & {
        loc.lower() for loc in fields["locations"]
    }
    law_hit = set(person.get("laws", [])) & set(fields["laws"]) & CHAIN_LAWS
    if loc_hit and law_hit:
        score += 35
        reasons.append("same hotspot + syndicate statute")
    elif loc_hit:
        score += 10
        reasons.append("same hotspot")
    elif law_hit:
        score += 8
        reasons.append("same syndicate statute")
    return score, reasons


def _cluster_of(index, person_id):
    for root, members in index["clusters"].items():
        if person_id in members:
            return root, members
    return person_id, [person_id]


def _candidate_ids(index, fields):
    candidates = []
    for person_id in fields["person_ids"]:
        if person_id in index["people"]:
            candidates.append(person_id)
    for name in fields["names"]:
        candidates.extend(index["name_to_ids"].get(name.lower(), []))
    for phone in fields["phones"]:
        candidates.extend(index["phone_to_ids"].get(phone, []))
    for tag in fields["phone_tags"]:
        candidates.extend(index["tag_to_ids"].get(tag, []))
    for vehicle in fields["vehicles"]:
        candidates.extend(index["vehicle_to_ids"].get(vehicle, []))
    for weapon in fields["weapons"]:
        candidates.extend(index["weapon_to_ids"].get(weapon, []))
    for loc in fields["locations"]:
        candidates.extend(index["location_to_ids"].get(loc.lower(), []))
    return list(dict.fromkeys(candidates))


def auto_place(index, fields):
    scored = []
    for person_id in _candidate_ids(index, fields):
        score, reasons = _score_person(index["people"][person_id], fields)
        if score > 0:
            scored.append((score, person_id, reasons))
    scored.sort(key=lambda row: row[0], reverse=True)

    if scored and scored[0][0] >= 25:
        score, person_id, reasons = scored[0]
        root, members = _cluster_of(index, person_id)
        return {
            "action": "MERGE",
            "person_id": person_id,
            "name": index["people"][person_id]["name"],
            "confidence": min(99.0, 40 + score * 0.55),
            "reasons": reasons,
            "cluster_size": len(members),
            "cluster_id": root,
            "alternates": [
                {
                    "person_id": pid,
                    "name": index["people"][pid]["name"],
                    "score": sc,
                    "reasons": rs,
                }
                for sc, pid, rs in scored[1:4]
            ],
        }

    new_id = fields["person_ids"][0] if fields["person_ids"] else "NEW_UNIDENTIFIED"
    nearest = scored[0] if scored else None
    root, members = _cluster_of(index, nearest[1]) if nearest else (new_id, [new_id])
    return {
        "action": "CREATE_AND_PARK",
        "person_id": new_id,
        "name": fields["names"][0] if fields["names"] else new_id,
        "confidence": 35.0 if nearest else 10.0,
        "reasons": ["no exact identity; parked on nearest feature cluster"]
        + (nearest[2] if nearest else []),
        "cluster_size": len(members),
        "cluster_id": root,
        "alternates": [],
        "nearest": (
            {
                "person_id": nearest[1],
                "name": index["people"][nearest[1]]["name"],
                "score": nearest[0],
            }
            if nearest
            else None
        ),
    }


def expand_links(index, person_id):
    person = index["people"].get(person_id)
    if person is None:
        return {"person": None, "cluster_id": None, "cluster_size": 0, "linked_people": []}

    root, members = _cluster_of(index, person_id)
    linked = []
    for other_id in members:
        if other_id == person_id:
            continue
        other = index["people"][other_id]
        shared = {
            "phones": sorted(set(person["phones"]) & set(other["phones"])),
            "phone_tags": sorted(set(person["phone_tags"]) & set(other["phone_tags"])),
            "vehicles": sorted(set(person["vehicles"]) & set(other["vehicles"])),
            "weapons": sorted(set(person["weapons"]) & set(other["weapons"])),
            "locations": sorted(set(person["locations"]) & set(other["locations"])),
            "firs": sorted(set(person["firs"]) & set(other["firs"])),
        }
        evidence = [key for key, values in shared.items() if values]
        linked.append(
            {
                "person_id": other_id,
                "name": other["name"],
                "chain_hits": other["chain_hits"],
                "firs": other["firs"][:8],
                "evidence": evidence,
                "shared": {key: values for key, values in shared.items() if values},
            }
        )
    linked.sort(key=lambda row: (len(row["evidence"]), row["chain_hits"]), reverse=True)
    return {
        "person": person,
        "cluster_id": root,
        "cluster_size": len(members),
        "linked_people": linked,
    }


def ingest(text, index=None, persist=True):
    if index is None:
        index = load_index()
    fields = extract_fields(text)
    placement = auto_place(index, fields)
    dossier = expand_links(index, placement["person_id"])
    result = {"recovered_fields": fields, "placement": placement, "dossier": dossier}
    if persist:
        os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"text": text[:500], "placement": placement}) + "\n")
    return result


def print_ingest(result):
    fields = result["recovered_fields"]
    place = result["placement"]
    dossier = result["dossier"]

    print("RECOVERED FIELDS (including what clerks usually skip)")
    print("-" * 56)
    print(f"  names       : {fields['names'] or '-'}")
    print(f"  person IDs  : {fields['person_ids'] or '-'}")
    print(f"  phones      : {fields['phones'] or '-'}")
    print(f"  PH_ tags    : {fields['phone_tags'] or '-'}")
    print(f"  vehicles    : {fields['vehicles'] or '-'}")
    print(f"  serials     : {fields['weapons'] or '-'}")
    print(f"  laws        : {fields['laws'] or '-'}")
    print(f"  locations   : {fields['locations'] or '-'}")
    print(f"  chain FIR   : {fields['is_chain']}")

    print()
    print("AUTO-PLACEMENT (system chose the slot, not the operator)")
    print("-" * 56)
    print(f"  action      : {place['action']}")
    print(f"  attached to : {place['name']}  [{place['person_id']}]")
    print(f"  confidence  : {place['confidence']:.1f}%")
    print(f"  cluster     : {place['cluster_id']}  ({place['cluster_size']} identities)")
    print(f"  because     : {'; '.join(place['reasons'])}")
    if place.get("alternates"):
        print("  other slots considered:")
        for alt in place["alternates"][:3]:
            print(f"    - {alt['name']} [{alt['person_id']}] score={alt['score']}")

    person = dossier.get("person") or {}
    print()
    print("FULL LINK MAP FOR THIS IDENTITY")
    print("-" * 56)
    print(f"  FIRs        : {len(person.get('firs', []))}  {person.get('firs', [])[:8]}")
    print(f"  phones      : {person.get('phones', [])}")
    print(f"  vehicles    : {person.get('vehicles', [])}")
    print(f"  serials     : {person.get('weapons', [])}")
    print(f"  hotspots    : {person.get('locations', [])}")
    print(f"  chain hits  : {person.get('chain_hits', 0)}")

    linked = dossier.get("linked_people") or []
    print()
    print(f"HIDDEN ASSOCIATES ({len(linked)}) — shared assets across FIRs")
    print("-" * 56)
    if not linked:
        print("  none. this identity is currently isolated.")
        return
    for row in linked[:20]:
        evidence = ", ".join(row["evidence"]) or "cluster"
        print(
            f"  {row['name']:28s} [{row['person_id']}]  "
            f"via {evidence}  chain_firs={row['chain_hits']}"
        )
        for kind, values in row["shared"].items():
            print(f"      {kind}: {values[:4]}")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest a FIR. The system places it and expands every hidden link."
    )
    parser.add_argument("text", nargs="?", help="Raw FIR / officer note")
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--file", help="Read FIR text from a file")
    args = parser.parse_args()

    if args.rebuild_index or not os.path.exists(INDEX_PATH):
        build_index()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            text = handle.read()
    elif args.text:
        text = args.text
    else:
        parser.print_help()
        return

    print_ingest(ingest(text))


if __name__ == "__main__":
    main()
