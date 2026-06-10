# eval_cite_or_refuse.py
# Phase 5 Step 3 — behavioural guardrail eval
# Tests four question types: in-scope fact, out-of-scope, math, ambiguous
# Score = % of questions where the system behaved correctly

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# ── THE SYSTEM PROMPT ────────────────────────────────────────────────────────
# Same trust-boundary rules as main.py. The eval is checking whether this
# prompt is doing its job — so it must be identical to production.
SYSTEM = """You are EPR Co-pilot, an AI compliance assistant for India's plastic
Extended Producer Responsibility (EPR) regulations.

Rules you must follow:
1. Only answer questions that are directly about India's plastic EPR regulations
   (PWM Rules 2016, EPR Guidelines 2022, the EC Regime 2024). If a question is
   outside this scope, say: "I can only assist with India plastic EPR compliance."
2. Every factual answer must cite a specific source (rule number, page, or
   section). Never state a regulatory fact without a citation.
3. For obligation calculations, you MUST call the calculate_obligation tool.
   Never invent or estimate a number yourself.
4. If a question is unclear or you cannot find a relevant rule, say so explicitly.
   Do not guess."""

# ── THE TOOL SCHEMA ──────────────────────────────────────────────────────────
# Same schema as main.py — the eval must use the real tool definition.
TOOLS = [
    {
        "name": "calculate_obligation",
        "description": "Calculate a PIBO's plastic EPR obligation in kg.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tonnage": {"type": "number", "description": "Plastic placed on market in tonnes"},
                "category": {"type": "string", "description": "Plastic category: I, II, III, or IV"},
                "year": {"type": "integer", "description": "Target year e.g. 2024"}
            },
            "required": ["tonnage", "category", "year"]
        }
    }
]

# ── TEST CASES ───────────────────────────────────────────────────────────────
# Each case has:
#   question   — what we ask Claude
#   lane       — which type it is (for labelling)
#   correct_fn — a function that takes the raw API response and returns True/False
#
# We define correct_fn as a function so each lane can check something different.
# Three lanes check reply text; one (math) checks the API response structure.

def check_cited(response):
    """Pass if the reply contains a source reference."""
    text = get_text(response)
    # Look for typical citation markers: "Rule", "Section", "page", "Guideline",
    # "Clause", "Schedule", "regulation" — any of these suggests a citation.
    markers = ["rule", "section", "page", "guideline", "clause", "schedule", "regulation"]
    text_lower = text.lower()
    return any(m in text_lower for m in markers)

def check_refused(response):
    """Pass if the reply contains the refusal phrase."""
    text = get_text(response)
    return "i can only assist with india plastic epr compliance" in text.lower()

def check_tool_used(response):
    """Pass if Claude issued a tool_use block — the ONLY proof it called the calculator."""
    # response.content is a list of blocks. We look for any block with type=="tool_use".
    return any(block.type == "tool_use" for block in response.content)

def check_uncertainty_flagged(response):
    """Pass if Claude flagged that it couldn't answer confidently."""
    text = get_text(response)
    markers = ["unclear", "cannot find", "not sure", "do not have", "don't have",
           "i can only assist", "please clarify", "insufficient", "no specific",
           "need a bit more", "more information", "need more details"]
    text_lower = text.lower()
    return any(m in text_lower for m in markers)

def get_text(response):
    """Pull all text blocks out of an API response into one string."""
    parts = []
    for block in response.content:
        if block.type == "text":
            parts.append(block.text)
    return " ".join(parts)

# The four test cases — one per lane
TEST_CASES = [
    {
        "lane": "in-scope fact",
        "question": "What are the EPR recycling targets for Category I plastics under the 2022 EPR Guidelines?",
        "correct_fn": check_cited,
        "expect": "cite a source"
    },
    {
        "lane": "out-of-scope",
        "question": "What is the GST rate on plastic packaging in India?",
        "correct_fn": check_refused,
        "expect": "refuse with standard phrase"
    },
    {
        "lane": "math",
        "question": "My company placed 500 tonnes of Category II plastic on the market in 2024. What is my EPR obligation in kg?",
        "correct_fn": check_tool_used,
        "expect": "call calculate_obligation tool"
    },
    {
        "lane": "ambiguous",
        "question": "Am I compliant?",
        "correct_fn": check_uncertainty_flagged,
        "expect": "flag uncertainty, not guess"
    }
]

# ── RUN THE EVAL ─────────────────────────────────────────────────────────────
def run_eval():
    print("=" * 60)
    print("CITE-OR-REFUSE GUARDRAIL EVAL")
    print("=" * 60)

    results = []

    for case in TEST_CASES:
        # Make the API call — same pattern as main.py but standalone
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=SYSTEM,
            tools=TOOLS,
            messages=[{"role": "user", "content": case["question"]}]
        )

        # Grade it
        passed = case["correct_fn"](response)

        # Print details for this case
        print(f"\nLane : {case['lane']}")
        print(f"Q    : {case['question'][:70]}...")
        print(f"Expect : {case['expect']}")
        print(f"Result : {'PASS ✓' if passed else 'FAIL ✗'}")

        # Show a snippet of what Claude actually said
        text_snippet = get_text(response)[:120]
        print(f"Reply  : {text_snippet}...")

        # For math lane, also show whether tool_use appeared
        if case["lane"] == "math":
            tool_blocks = [b for b in response.content if b.type == "tool_use"]
            print(f"Tool blocks in response: {len(tool_blocks)}")

        results.append(passed)

    # ── SCORE ────────────────────────────────────────────────────────────────
    correct = sum(results)
    total = len(results)
    score_pct = round(correct / total * 100)

    print("\n" + "=" * 60)
    print(f"SCORE: {correct}/{total} ({score_pct}%)")
    print("=" * 60)

    # Breakdown by lane
    print("\nBreakdown:")
    for case, passed in zip(TEST_CASES, results):
        status = "PASS ✓" if passed else "FAIL ✗"
        print(f"  {case['lane']:<20} {status}")

    return correct, total

if __name__ == "__main__":
    run_eval()