"""
synthetic_data.py — Phase 4, Step 4-i

Generates claim packets with KNOWN labels for testing the discrepancy checks.
No real recycler data, ever — these are invented packets with deliberately
seeded fraud, so we know in advance which check SHOULD fire.

A claim packet is a plain dict describing one recycling claim.
The label tells us the ground truth: "plausible", or which fraud was seeded.
"""

import random


# A pool of fake recycler IDs to draw from — just for realism.
RECYCLER_IDS = ["REC-001", "REC-014", "REC-042", "REC-077", "REC-103"]


def make_legit_packet():
    """Build a packet where every number is plausible.
    Ground-truth label: 'plausible'."""
    capacity = random.choice([50, 100, 200, 500])      # licensed tonnes/year
    claimed  = round(capacity * random.uniform(0.3, 0.9), 1)  # well under capacity
    input_t  = round(claimed * random.uniform(1.0, 1.2), 1)   # received a bit more than claimed
    output_t = round(input_t * random.uniform(0.85, 0.98), 1) # output < input (process loss)

    return {
        "recycler_id":           random.choice(RECYCLER_IDS),
        "registered_capacity_t": capacity,
        "claimed_recycled_t":    claimed,
        "input_t":               input_t,
        "output_t":              output_t,
        "cert_year":             2024,
        "registration_year":     2022,   # registered BEFORE the cert — fine
        "label":                 "plausible",
    }


def make_capacity_fraud_packet():
    """Start from a legit packet, then bend claimed_recycled WAY past capacity.
    Ground-truth label: 'capacity'. (The 38x pattern.)"""
    packet = make_legit_packet()
    multiplier = random.choice([5, 12, 38])            # claim many times the capacity
    packet["claimed_recycled_t"] = round(packet["registered_capacity_t"] * multiplier, 1)
    packet["label"] = "capacity"
    return packet


def make_material_balance_fraud_packet():
    """Start from a legit packet, then bend output ABOVE input.
    You can't recycle more than you received.
    Ground-truth label: 'material_balance'."""
    packet = make_legit_packet()
    packet["output_t"] = round(packet["input_t"] * random.uniform(1.1, 1.5), 1)
    packet["label"] = "material_balance"
    return packet


def make_cross_doc_fraud_packet():
    """Start from a legit packet, then issue the cert BEFORE registration.
    A cert can't exist before the recycler was registered.
    Ground-truth label: 'cross_document'."""
    packet = make_legit_packet()
    packet["registration_year"] = 2023
    packet["cert_year"] = 2022        # cert predates registration — impossible
    packet["label"] = "cross_document"
    return packet


# A registry of all generators — makes it easy to build a mixed dataset.
GENERATORS = [
    make_legit_packet,
    make_capacity_fraud_packet,
    make_material_balance_fraud_packet,
    make_cross_doc_fraud_packet,
]


def make_dataset(n_each=2):
    """Build a mixed list: n_each packets from every generator.
    Returns a shuffled list so legit and fraud are interleaved."""
    dataset = []
    for generator in GENERATORS:
        for _ in range(n_each):
            dataset.append(generator())
    random.shuffle(dataset)
    return dataset


# Isolation test — runs ONLY when this file is run directly.
if __name__ == "__main__":
    print("One legit packet:")
    print(make_legit_packet())
    print()
    print("One capacity-fraud packet:")
    print(make_capacity_fraud_packet())
    print()
    print("One material-balance-fraud packet:")
    print(make_material_balance_fraud_packet())
    print()
    print("One cross-document-fraud packet:")
    print(make_cross_doc_fraud_packet())
    print()
    print(f"A mixed dataset has {len(make_dataset())} packets.")