# calculator.py
# Phase 3, Step 3a: the deterministic obligation calculator.
# A pure function. Same inputs -> same output. Touches nothing else.

# --- The lookup table -------------------------------------------------
# Real CPCB figures. Source: EPR Guidelines 2022, p.27
# Gazette of India, Part II, Sec. 3(i)
# Table: "Minimum level of recycling (excluding end of life disposal)
#         of plastic packaging waste (% of EPR Target)"
#
# Key convention: "2024" means FY 2024-25, "2025" means FY 2025-26, etc.
# Coverage: FY 2024-25 onwards. Pre-2024 years are not in this table.
TARGETS = {
    "I": {
        "2024": 0.50,  # FY 2024-25 — EPR Guidelines 2022, p.27
        "2025": 0.60,  # FY 2025-26 — EPR Guidelines 2022, p.27
        "2026": 0.70,  # FY 2026-27 — EPR Guidelines 2022, p.27
        "2027": 0.80,  # FY 2027-28 and onwards — EPR Guidelines 2022, p.27
    },
    "II": {
        "2024": 0.30,  # FY 2024-25 — EPR Guidelines 2022, p.27
        "2025": 0.40,  # FY 2025-26 — EPR Guidelines 2022, p.27
        "2026": 0.50,  # FY 2026-27 — EPR Guidelines 2022, p.27
        "2027": 0.60,  # FY 2027-28 and onwards — EPR Guidelines 2022, p.27
    },
    "III": {
        "2024": 0.30,  # FY 2024-25 — EPR Guidelines 2022, p.27
        "2025": 0.40,  # FY 2025-26 — EPR Guidelines 2022, p.27
        "2026": 0.50,  # FY 2026-27 — EPR Guidelines 2022, p.27
        "2027": 0.60,  # FY 2027-28 and onwards — EPR Guidelines 2022, p.27
    },
    "IV": {
        "2024": 0.50,  # FY 2024-25 — EPR Guidelines 2022, p.27
        "2025": 0.60,  # FY 2025-26 — EPR Guidelines 2022, p.27
        "2026": 0.70,  # FY 2026-27 — EPR Guidelines 2022, p.27
        "2027": 0.80,  # FY 2027-28 and onwards — EPR Guidelines 2022, p.27
    },
}


def calculate_obligation(tonnage, category, year):
    """Return the minimum recycling obligation in kilograms.

    tonnage  -- plastic placed on the market, in tonnes (a number)
    category -- plastic category: "I", "II", "III", or "IV" (a string)
    year     -- FY start year, e.g. "2024" means FY 2024-25 (a string)
    """
    # 1. Look up the target percentage for this category and year.
    target = TARGETS[category][year]

    # 2. Convert tonnes to kilograms (1 tonne = 1000 kg).
    kg_on_market = tonnage * 1000

    # 3. The obligation is that weight times the target percentage.
    obligation_kg = kg_on_market * target

    # 4. Hand the number back. Nothing else touched.
    return obligation_kg


# --- Isolation test ---------------------------------------------------
if __name__ == "__main__":
    result = calculate_obligation(50, "I", "2024")
    print(f"50 tonnes, Category I, FY 2024-25 -> {result} kg")
    # Expected: 50 * 1000 * 0.50 = 25,000 kg  (old wrong answer was 35,000 kg)