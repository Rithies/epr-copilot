"""
discrepancy.py — Phase 4, Step 4-ii

Three deterministic discrepancy checks, each a PURE function.
Same trust boundary as calculator.py: this code renders the FLAG;
Claude only explains it. A claim cannot be called "plausible" unless
these checks actually ran and returned a verdict.

Each individual check returns either:
  - a (check_name, reason) tuple  → the check FIRED (something is wrong)
  - None                          → the check passed (nothing wrong)

run_all_checks() collects every fired check into one structured verdict.
"""

# How much more output than input we tolerate before flagging.
# Recycling always loses some material, so output should be BELOW input.
# We allow a small 5% margin for measurement noise.
LOSS_TOLERANCE = 0.05


def check_capacity(packet):
    """Flag if claimed recycled tonnage exceeds registered capacity.
    This is the 38x pattern from the fake-certificate crisis."""
    claimed  = packet["claimed_recycled_t"]
    capacity = packet["registered_capacity_t"]

    if claimed > capacity:
        reason = (
            f"Claimed recycled tonnage ({claimed} t) exceeds the recycler's "
            f"registered capacity ({capacity} t). A facility cannot recycle "
            f"more than it is licensed to handle."
        )
        return ("capacity", reason)
    return None


def check_material_balance(packet):
    """Flag if output exceeds input beyond the allowed loss tolerance.
    You cannot recycle more material than you received."""
    input_t  = packet["input_t"]
    output_t = packet["output_t"]
    ceiling  = input_t * (1 + LOSS_TOLERANCE)

    if output_t > ceiling:
        reason = (
            f"Reported output ({output_t} t) exceeds input ({input_t} t) "
            f"beyond the {int(LOSS_TOLERANCE * 100)}% tolerance. Recycling "
            f"cannot produce more material than it receives."
        )
        return ("material_balance", reason)
    return None


def check_cross_document(packet):
    """Flag if the certificate is dated before the recycler was registered.
    A certificate cannot exist before the entity that issued it."""
    cert_year         = packet["cert_year"]
    registration_year = packet["registration_year"]

    if cert_year < registration_year:
        reason = (
            f"Certificate year ({cert_year}) precedes the recycler's "
            f"registration year ({registration_year}). A certificate cannot "
            f"predate the registration of the facility that issued it."
        )
        return ("cross_document", reason)
    return None


# A list of all checks — adding a fourth check later is one more entry.
ALL_CHECKS = [
    check_capacity,
    check_material_balance,
    check_cross_document,
]


def run_all_checks(packet):
    """Run every check and assemble one structured verdict.
    Returns a dict: status + which checks fired + their reasons."""
    fired = []
    reasons = {}

    for check in ALL_CHECKS:
        result = check(packet)
        if result is not None:          # the check fired
            name, reason = result
            fired.append(name)
            reasons[name] = reason

    status = "flagged" if fired else "plausible"

    return {
        "recycler_id":  packet["recycler_id"],
        "status":       status,
        "checks_fired": fired,
        "reasons":      reasons,
    }


# Isolation test — runs ONLY when this file is run directly.
if __name__ == "__main__":
    # We import the generator so we can test against KNOWN labels.
    from synthetic_data import (
        make_legit_packet,
        make_capacity_fraud_packet,
        make_material_balance_fraud_packet,
        make_cross_doc_fraud_packet,
    )

    test_cases = [
        ("legit",          make_legit_packet()),
        ("capacity",       make_capacity_fraud_packet()),
        ("material_bal",   make_material_balance_fraud_packet()),
        ("cross_doc",      make_cross_doc_fraud_packet()),
    ]

    for name, packet in test_cases:
        verdict = run_all_checks(packet)
        print(f"--- {name} (label: {packet['label']}) ---")
        print(f"    status: {verdict['status']}")
        print(f"    checks_fired: {verdict['checks_fired']}")
        print()