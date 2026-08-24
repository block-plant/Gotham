"""Recover identifiers that officers and spaCy routinely drop or split."""
import re

CHAIN_LAWS = {"BNS 143", "BNS 103", "BNS 308"}

PATTERN_PERSON_ID = re.compile(r"\[ID:(P_[a-f0-9]+)\]", re.I)
PATTERN_NAME_ID = re.compile(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*\[ID:(P_[a-f0-9]+)\]")
PATTERN_PHONE_TAG = re.compile(r"(PH_[a-f0-9]+)", re.I)
PATTERN_PHONE = re.compile(r"(?:\+91[\-\s]?)[6-9]\d{9,13}")
PATTERN_WEAPON = re.compile(r"\[Serial:(W_[a-f0-9]+)\]", re.I)
PATTERN_VEHICLE = re.compile(r"[A-Z]{2}[\-\s]?\d{1,2}[\-\s]?[A-Z0-9]{1,2}[\-\s]?\d{4}")
PATTERN_LAW = re.compile(r"(BNS|IPC|NDPS|Arms Act)[\-\s]?\d{2,3}[A-Z]?", re.I)
PATTERN_SECTOR = re.compile(r"Sector[\-\s]?\d{1,3}", re.I)
PATTERN_HOTSPOT = re.compile(
    r"(NH[\-\s]?\d{1,3}\s+Junction|Industrial Area|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s(?:Road|Market|Station|Alley))",
    re.I,
)


def _norm_phone(raw):
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("91") and len(digits) > 10:
        digits = digits[2:]
    if len(digits) >= 10:
        return "+91-" + digits[:10]
    return raw.strip()


def extract_fields(text):
    """Pull every investigative field a clerk can miss in one pass."""
    names = []
    person_ids = []
    aliases = {}
    for name, pid in PATTERN_NAME_ID.findall(text):
        names.append(name.strip())
        person_ids.append(pid)
        aliases[pid] = name.strip()

    for pid in PATTERN_PERSON_ID.findall(text):
        if pid not in person_ids:
            person_ids.append(pid)

    phones = [_norm_phone(p) for p in PATTERN_PHONE.findall(text)]
    phone_tags = [t.upper() if t.startswith("PH") else t for t in PATTERN_PHONE_TAG.findall(text)]
    vehicles = [re.sub(r"\s+", "-", v.strip()) for v in PATTERN_VEHICLE.findall(text)]
    weapons = [w.upper() if w.startswith("W") else w for w in PATTERN_WEAPON.findall(text)]
    laws = [" ".join(m.group().split()) for m in PATTERN_LAW.finditer(text)]
    laws = [re.sub(r"(BNS|IPC|NDPS)\s*", lambda m: m.group(1).upper() + " ", law, count=1).strip() for law in laws]
    locations = PATTERN_SECTOR.findall(text) + PATTERN_HOTSPOT.findall(text)
    locations = list(dict.fromkeys(locations))

    return {
        "names": list(dict.fromkeys(names)),
        "person_ids": list(dict.fromkeys(person_ids)),
        "aliases": aliases,
        "phones": list(dict.fromkeys(phones)),
        "phone_tags": list(dict.fromkeys(phone_tags)),
        "vehicles": list(dict.fromkeys(vehicles)),
        "weapons": list(dict.fromkeys(weapons)),
        "laws": list(dict.fromkeys(laws)),
        "locations": locations,
        "is_chain": any(law in CHAIN_LAWS for law in laws),
        "missed_by_humans": {
            "person_ids": person_ids,
            "phone_tags": phone_tags,
            "weapons": weapons,
        },
    }
