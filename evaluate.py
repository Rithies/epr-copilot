"""
evaluate.py — Phase 5, Step 1

An EVAL is a test with a SCORE. The Phase 4 isolation tests asked
"did it work?" (yes/no). This asks "how WELL does it work?" — two
numbers, precision and recall, that we can track as we change things.

Pure code: no Claude, no API call, no tokens. We reuse two pieces we
already built and proved:
  - synthetic_data.make_dataset() — labelled packets (the golden set)
  - discrepancy.run_all_checks()  — the verdict under test

We collapse both sides to one yes/no question — "fraud or not" — and
sort every packet into one of four buckets, then compute the scores.
"""

from synthetic_data import make_dataset
from discrepancy import run_all_checks


def is_really_fraud(packet):
    """Ground truth. Any label that isn't 'plausible' is seeded fraud."""
    return packet["label"] != "plausible"


def did_we_flag(packet):
    """Our system's call. Run the real checks; did the verdict flag it?"""
    verdict = run_all_checks(packet)
    return verdict["status"] == "flagged"


def evaluate(dataset):
    """Sort every packet into the 2x2 grid, then score it.
    Returns a dict of the four counts plus precision and recall."""
    tp = 0   # truly fraud  AND we flagged   -> caught fraud
    fp = 0   # truly legit  AND we flagged   -> false alarm
    fn = 0   # truly fraud  AND we passed    -> missed fraud
    tn = 0   # truly legit  AND we passed    -> passed legit

    for packet in dataset:
        fraud   = is_really_fraud(packet)
        flagged = did_we_flag(packet)

        if fraud and flagged:
            tp += 1
        elif (not fraud) and flagged:
            fp += 1
        elif fraud and (not flagged):
            fn += 1
        else:                       # not fraud and not flagged
            tn += 1

    # precision = of everything we FLAGGED, how much was real fraud?
    # recall    = of all the REAL fraud, how much did we CATCH?
    # Guard against divide-by-zero: if we flagged nothing, precision is
    # undefined — we report 0.0 and let the counts tell the real story.
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision,
        "recall":    recall,
    }


if __name__ == "__main__":
    # ----------------------------------------------------------------
    # PART 1: golden set — 100 shuffled packets, known labels.
    # ----------------------------------------------------------------
    dataset = make_dataset(n_each=25)
    scores = evaluate(dataset)

    print("=" * 45)
    print("PART 1: golden set")
    print("=" * 45)
    print(f"Dataset size: {len(dataset)} packets\n")
    print("Confusion matrix")
    print(f"  true positives  (caught fraud):  {scores['tp']}")
    print(f"  false positives (false alarm):   {scores['fp']}")
    print(f"  false negatives (missed fraud):  {scores['fn']}")
    print(f"  true negatives  (passed legit):  {scores['tn']}\n")
    print(f"Precision: {scores['precision']:.2%}")
    print(f"Recall:    {scores['recall']:.2%}")

    # ----------------------------------------------------------------
    # PART 2: stress test — hand-crafted edge cases the golden set
    # can't see. Each packet has a label and an expected verdict so
    # we can print PASS/FAIL per case, not just aggregate scores.
    # ----------------------------------------------------------------
    print("\n" + "=" * 45)
    print("PART 2: stress test (edge cases)")
    print("=" * 45)

    stress_cases = [
        # Edge case 1: claimed == capacity exactly.
        # > is strict, so this should PASS (not flagged).
        # Label is "capacity" because a real auditor would be suspicious,
        # but our check's boundary decision is >, not >=.
        # Expected verdict: plausible (known limitation).
        {
            "label": "capacity",            # truly fraud by intent
            "expected_status": "plausible", # but our check misses it — known gap
            "description": "capacity exactly at limit (claimed == registered)",
            "recycler_id": "REC-001",
            "registered_capacity_t": 100.0,
            "claimed_recycled_t":    100.0,  # exactly equal — NOT > capacity
            "input_t":               110.0,
            "output_t":              95.0,
            "cert_year":             2024,
            "registration_year":     2022,
        },
        # Edge case 2: two checks fire at once.
        # capacity fraud AND material balance fraud in the same packet.
        # Both checks should fire; status should be "flagged".
        {
            "label": "capacity",            # seeded as fraud
            "expected_status": "flagged",
            "description": "double fraud: capacity AND material balance both violated",
            "recycler_id": "REC-042",
            "registered_capacity_t": 100.0,
            "claimed_recycled_t":    500.0,  # 5x capacity — fires check_capacity
            "input_t":               80.0,
            "output_t":              100.0,  # output > input * 1.05 — fires check_material_balance
            "cert_year":             2024,
            "registration_year":     2022,
        },
        # Edge case 3: material balance exactly at the tolerance boundary.
        # output == input * 1.05 exactly. > is strict, so should PASS.
        {
            "label": "plausible",           # we expect this to pass
            "expected_status": "plausible",
            "description": "material balance exactly at 5% tolerance (output == input * 1.05)",
            "recycler_id": "REC-014",
            "registered_capacity_t": 200.0,
            "claimed_recycled_t":    80.0,
            "input_t":               100.0,
            "output_t":              105.0,  # exactly input * 1.05 — NOT > ceiling
            "cert_year":             2024,
            "registration_year":     2022,
        },
        # Edge case 4: cert year == registration year.
        # < is strict, so same year should PASS.
        {
            "label": "plausible",
            "expected_status": "plausible",
            "description": "cert year == registration year (same year, not before)",
            "recycler_id": "REC-077",
            "registered_capacity_t": 200.0,
            "claimed_recycled_t":    80.0,
            "input_t":               100.0,
            "output_t":              90.0,
            "cert_year":             2022,
            "registration_year":     2022,  # same year — NOT < registration_year
        },
    ]

    all_passed = True
    for case in stress_cases:
        verdict = run_all_checks(case)
        actual   = verdict["status"]
        expected = case["expected_status"]
        fired    = verdict["checks_fired"]
        ok       = "PASS" if actual == expected else "FAIL"
        if ok == "FAIL":
            all_passed = False
        print(f"\n  [{ok}] {case['description']}")
        print(f"        expected={expected}  got={actual}  checks_fired={fired}")

    print()
    if all_passed:
        print("All stress cases matched expected outcomes.")
    else:
        print("Some stress cases did not match — review above.")