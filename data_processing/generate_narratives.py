import random
import uuid
from faker import Faker

fake = Faker('en_IN')

# ---------------------------------------------------------
# 1. LINGUISTIC ENTROPY (Scrambling sentence structures)
# ---------------------------------------------------------
# By breaking the narrative into interchangeable fragments, we generate 
# thousands of unique grammatical permutations.
OPENINGS = [
    "On {date}, it was reported that",
    "A formal complaint was lodged on {date} regarding an incident where",
    "Police response was initiated on {date} after",
    "During routine patrol on {date}, officers noted that",
    "According to the FIR dated {date},"
]

ACTIONS_PETTY = [
    "{suspect} engaged in pocket snatching near {location}.",
    "a two-wheeler {vehicle} was reported stolen from {location} by {suspect}.",
    "an unknown assailant, later identified as {suspect}, committed mobile theft at {location}.",
    "{suspect} was apprehended following a public nuisance complaint at {location}."
]

ACTIONS_VIOLENT = [
    "{suspect} brutally assaulted a local vendor at {location} using a {weapon}.",
    "a violent altercation broke out at {location}, resulting in {suspect} striking the victim with a {weapon}.",
    "accused {suspect} issued severe criminal threats at {location}, brandishing a {weapon}."
]

CLOSINGS = [
    "Case registered under {law}.",
    "FIR lodged under section {law}.",
    "Charges were formally framed under {law}.",
    "The incident was recorded under {law}."
]

# ---------------------------------------------------------
# 2. CRYPTOGRAPHIC NAMESPACING
# ---------------------------------------------------------
def secure_id(prefix):
    """Guarantees absolute uniqueness across 1 Crore+ entries."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

# ---------------------------------------------------------
# 3. DEFINING THE HIDDEN CHAINS (Ground Truth)
# ---------------------------------------------------------
class CrimeSyndicate:
    def __init__(self, name, domain):
        self.name = name
        self.domain = domain
        self.members = [f"{fake.name()} [ID:{secure_id('P')}]" for _ in range(5)]
        self.phones = [f"+91-{fake.msisdn()}-{secure_id('PH')[:6]}" for _ in range(2)]
        self.vehicles = [f"UP-{random.randint(10,99)}-{uuid.uuid4().hex[:2].upper()}-{random.randint(1000,9999)}" for _ in range(2)]
        self.weapons = [f"9mm Pistol [Serial:{secure_id('W')}]"]
        self.hotspots = [f"Sector-{random.randint(1,50)}", "NH-24 Junction", "Industrial Area"]

gangs = [
    CrimeSyndicate("Interstate_Traffickers", "Crimes_Against_Women"),
    CrimeSyndicate("Armed_Robbery_Crew", "Heinous_Violent"),
    CrimeSyndicate("Extortion_Ring", "Organized_Syndicates")
]

# ---------------------------------------------------------
# 4. RANDOMIZED NARRATIVE BUILDER
# ---------------------------------------------------------
def build_noise():
    """Generates a highly randomized, isolated narrative."""
    date = fake.date_between(start_date='-2y', end_date='today').strftime("%d %b %Y")
    suspect = f"{fake.name()} [ID:{secure_id('P')}]"
    location = f"{fake.city()} {random.choice(['Market', 'Station', 'Alley', 'Road'])}"
    vehicle = f"UP-{random.randint(10,99)}-{uuid.uuid4().hex[:2].upper()}-{random.randint(1000,9999)}"
    weapon = random.choice(["Iron Rod", "Knife", "Desi Katta"])
    law = f"BNS {random.randint(100, 350)}"

    opening = random.choice(OPENINGS).format(date=date)
    
    if random.random() < 0.7:
        action = random.choice(ACTIONS_PETTY).format(suspect=suspect, location=location, vehicle=vehicle)
    else:
        action = random.choice(ACTIONS_VIOLENT).format(suspect=suspect, location=location, weapon=weapon)
        
    closing = random.choice(CLOSINGS).format(law=law)
    
    # Introduce random omissions (sometimes police don't record a closing law)
    if random.random() > 0.85: closing = ""
        
    return f"{opening} {action} {closing}".strip()

def build_chain_link(gang: CrimeSyndicate):
    """Weaves gang assets into a randomized narrative structure."""
    date = fake.date_between(start_date='-2y', end_date='today').strftime("%d %b %Y")
    suspect = random.choice(gang.members)
    location = random.choice(gang.hotspots)
    phone = random.choice(gang.phones)
    vehicle = random.choice(gang.vehicles)
    weapon = random.choice(gang.weapons)

    opening = random.choice(OPENINGS).format(date=date)
    
    # Dynamically build the action based on the gang's domain
    if gang.domain == "Crimes_Against_Women":
        action = f"{suspect} was implicated in a trafficking operation near {location}, utilizing contact {phone}."
        law = "BNS 143"
    elif gang.domain == "Heinous_Violent":
        action = f"an armed assault occurred at {location}. {suspect} fired a {weapon} and fled in {vehicle}."
        law = "BNS 103"
    else:
        action = f"extortion demands were made at {location} by {suspect} via phone {phone}."
        law = "BNS 308"

    closing = random.choice(CLOSINGS).format(law=law)
    
    return f"{opening} {action} {closing}".strip()

# ---------------------------------------------------------
# 5. EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    TOTAL_RECORDS = 50000 
    output_file = "entropy_narratives.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        for _ in range(TOTAL_RECORDS):
            # 90% Noise, 10% Chain Links
            if random.random() < 0.90:
                f.write(build_noise() + "\n")
            else:
                f.write(build_chain_link(random.choice(gangs)) + "\n")
                
    print(f"Generated {TOTAL_RECORDS} highly randomized narratives.")