# calculator.py
# Phase 3, Step 3a: the deterministic obligation calculator.
# A pure function. Same inputs -> same output. Touches nothing else.

# --- The lookup table -------------------------------------------------
# PLACEHOLDER NUMBERS - replace with the real CPCB targets from the
# EPR Guidelines (your retrieve.py pulled the Category I table, p.27).
# Structure: TARGETS[category][year] = target percentage (as a decimal).
TARGETS = {
    "I":   {"2022": 0.50, "2023": 0.60, "2024": 0.70, "2025": 0.80},
    "II":  {"2022": 0.30, "2023": 0.40, "2024": 0.50, "2025": 0.60},
    "III": {"2022": 0.10, "2023": 0.20, "2024": 0.30, "2025": 0.40},
    "IV":  {"2022": 0.10, "2023": 0.20, "2024": 0.30, "2025": 0.40},
}


def calculate_obligation(tonnage, category, year):
    """Return the minimum recycling obligation in kilograms.

    tonnage  -- plastic placed on the market, in tonnes (a number)
    category -- plastic category: "I", "II", "III", or "IV" (a string)
    year     -- financial year, e.g. "2024" (a string)
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
# This block runs ONLY when you do `python3 calculator.py` directly.
# It does NOT run when main.py imports this file later.
if __name__ == "__main__":
    result = calculate_obligation(50, "I", "2024")
    print(f"50 tonnes, Category I, 2024 -> {result} kg")