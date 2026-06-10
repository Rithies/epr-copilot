# test_calculator.py
# Phase 5: calculation-correctness eval.
# PRD metric: "Calculation correctness: 100% on the target-calculation test set."
#
# Pure code — no Claude, no tokens, no API calls.
# Each case: known inputs → expected output derived from p.27 table.
# Formula: tonnage * 1000 * target_percentage = obligation_kg

from calculator import calculate_obligation

# --- Test cases -------------------------------------------------------
# Each tuple: (tonnage, category, year, expected_kg, description)
# Expected values are hand-calculated from the real p.27 table.
# e.g. 1000t, Cat I, 2024 → 1000 * 1000 * 0.50 = 500,000 kg

TEST_CASES = [
    # Category I
    (1000, "I",   "2024", 500_000.0, "Cat I   FY2024-25: 1000t × 50%"),
    (1000, "I",   "2025", 600_000.0, "Cat I   FY2025-26: 1000t × 60%"),
    (1000, "I",   "2026", 700_000.0, "Cat I   FY2026-27: 1000t × 70%"),
    (1000, "I",   "2027", 800_000.0, "Cat I   FY2027-28: 1000t × 80%"),
    # Category II
    (1000, "II",  "2024", 300_000.0, "Cat II  FY2024-25: 1000t × 30%"),
    (1000, "II",  "2025", 400_000.0, "Cat II  FY2025-26: 1000t × 40%"),
    (1000, "II",  "2026", 500_000.0, "Cat II  FY2026-27: 1000t × 50%"),
    (1000, "II",  "2027", 600_000.0, "Cat II  FY2027-28: 1000t × 60%"),
    # Category III
    (1000, "III", "2024", 300_000.0, "Cat III FY2024-25: 1000t × 30%"),
    (1000, "III", "2025", 400_000.0, "Cat III FY2025-26: 1000t × 40%"),
    (1000, "III", "2026", 500_000.0, "Cat III FY2026-27: 1000t × 50%"),
    (1000, "III", "2027", 600_000.0, "Cat III FY2027-28: 1000t × 60%"),
    # Category IV
    (1000, "IV",  "2024", 500_000.0, "Cat IV  FY2024-25: 1000t × 50%"),
    (1000, "IV",  "2025", 600_000.0, "Cat IV  FY2025-26: 1000t × 60%"),
    (1000, "IV",  "2026", 700_000.0, "Cat IV  FY2026-27: 1000t × 70%"),
    (1000, "IV",  "2027", 800_000.0, "Cat IV  FY2027-28: 1000t × 80%"),
    # Different tonnages — verifies the formula scales correctly
    (500,  "I",   "2024", 250_000.0, "Cat I   FY2024-25: 500t  × 50%"),
    (100,  "II",  "2027",  60_000.0, "Cat II  FY2027-28: 100t  × 60%"),
    (1,    "IV",  "2024",     500.0, "Cat IV  FY2024-25: 1t    × 50%"),
]

# --- Runner -----------------------------------------------------------
def run_tests():
    passed = 0
    failed = 0

    for tonnage, category, year, expected, description in TEST_CASES:
        actual = calculate_obligation(tonnage, category, year)
        if actual == expected:
            print(f"✅ PASS  {description}")
            passed += 1
        else:
            print(f"❌ FAIL  {description}")
            print(f"        expected {expected} kg, got {actual} kg")
            failed += 1

    total = passed + failed
    print(f"\n{passed}/{total} passed")
    if failed == 0:
        print("Calculation correctness: 100% ✅  (PRD metric met)")

if __name__ == "__main__":
    run_tests()