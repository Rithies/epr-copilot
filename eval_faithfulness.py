"""
eval_faithfulness.py — Phase 5, Step 2 (v2: structured output)

EXPLANATION FAITHFULNESS: does Claude's prose narrative match the checks
that actually fired — nothing more, nothing less?

The trust boundary says: code flags, Claude explains.
This eval enforces the second half of that contract.

v1 used keyword scanning on free prose — too blunt, produced false
positives when Claude mentioned check-related words while explaining
that a check PASSED. v2 fixes this with structured output: Claude
returns JSON with an explicit list of the checks it is explaining,
so the comparison is exact — no guessing from word choice.

For each test packet we:
  1. Run run_all_checks()          -> get the verdict (checks_fired)
  2. Ask Claude for structured JSON -> {"checks_explained": [...], "narrative": "..."}
  3. Read checks_explained directly -> exact set Claude explained
  4. Compare explained vs fired    -> FAITHFUL or UNFAITHFUL

We use a small set (not 100 packets) because each case costs one API call.
"""

import json
from anthropic import Anthropic
from dotenv import load_dotenv
from discrepancy import run_all_checks
from synthetic_data import (
    make_legit_packet,
    make_capacity_fraud_packet,
    make_material_balance_fraud_packet,
    make_cross_doc_fraud_packet,
)

load_dotenv()
client = Anthropic()


def ask_claude_to_explain(verdict, packet):
    """One Claude API call: give Claude the verdict and packet numbers.
    Ask for structured JSON — an explicit list of checks explained
    plus a narrative. Return the parsed JSON dict.

    The system prompt instructs Claude to return ONLY JSON, no prose
    wrapper, no markdown fences — so we can parse it directly.
    """
    system = (
        "You are a compliance assistant. You will be given a recycling claim "
        "verdict and the packet numbers. Respond ONLY with a JSON object — "
        "no preamble, no markdown fences, no explanation outside the JSON. "
        "The JSON must have exactly two keys:\n"
        '  "checks_explained": a list containing ONLY the names of checks '
        "that actually fired (use exact names: capacity, material_balance, "
        "cross_document). If no checks fired, return an empty list [].\n"
        '  "narrative": a 2-3 sentence plain-language explanation for a '
        "compliance officer. Only explain checks that fired. "
        "If no checks fired, say the claim passed all checks."
    )

    prompt = (
        f"Verdict:\n{verdict}\n\n"
        f"Claim packet:\n{packet}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text

    # Strip markdown fences if Claude added them despite instructions.
    # This is defensive — Claude usually obeys, but strip just in case.
    clean = raw.strip()
    if clean.startswith("```"):
        # Remove the opening fence line and closing fence
        lines = clean.splitlines()
        clean = "\n".join(lines[1:-1]).strip()

    return json.loads(clean)   # parse JSON string → Python dict


def evaluate_faithfulness(test_cases):
    """Run the faithfulness check on every test case.
    Returns a list of result dicts, one per case."""
    results = []

    for label, packet in test_cases:
        # Step 1: run the real checks — free, deterministic.
        verdict = run_all_checks(packet)
        fired_set = set(verdict["checks_fired"])       # e.g. {"capacity"}

        # Step 2: ask Claude for structured JSON.
        structured = ask_claude_to_explain(verdict, packet)

        # Step 3: read the list Claude returned — exact, no scanning.
        mentioned_set = set(structured["checks_explained"])  # e.g. {"capacity"}

        # Step 4: compare.
        # extra   = Claude explained a check that did NOT fire (dangerous)
        # missing = Claude failed to explain a check that DID fire (incomplete)
        extra   = mentioned_set - fired_set
        missing = fired_set - mentioned_set

        faithful = (len(extra) == 0 and len(missing) == 0)

        results.append({
            "label":        label,
            "fired":        fired_set,
            "mentioned":    mentioned_set,
            "extra":        extra,
            "missing":      missing,
            "faithful":     faithful,
            "narrative":    structured["narrative"],
        })

    return results


if __name__ == "__main__":
    # Small set — one of each type. Four API calls total.
    test_cases = [
        ("legit",          make_legit_packet()),
        ("capacity",       make_capacity_fraud_packet()),
        ("material_bal",   make_material_balance_fraud_packet()),
        ("cross_doc",      make_cross_doc_fraud_packet()),
    ]

    print("Running faithfulness eval (structured output) — 4 API calls...\n")
    results = evaluate_faithfulness(test_cases)

    faithful_count = 0
    for r in results:
        status = "FAITHFUL  " if r["faithful"] else "UNFAITHFUL"
        print(f"[{status}] label={r['label']}")
        print(f"  fired:     {r['fired']}")
        print(f"  mentioned: {r['mentioned']}")
        if r["extra"]:
            print(f"  !! EXTRA (invented):  {r['extra']}")
        if r["missing"]:
            print(f"  !! MISSING (dropped): {r['missing']}")
        print(f"  narrative: {r['narrative'][:120]}...")
        print()
        if r["faithful"]:
            faithful_count += 1

    total = len(results)
    print(f"Faithfulness score: {faithful_count}/{total} "
          f"({faithful_count/total:.0%})")
