# test_tools.py
# Phase 3, Step 3b: prove the tool-use handshake works in isolation.
# Run with:  python3 test_tools.py
# (main.py is NOT touched yet — this is the isolation test.)

import anthropic
from dotenv import load_dotenv
from calculator import calculate_obligation
load_dotenv()

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

# --- Piece 1: the tool schema (the "menu card") ---
TOOLS = [
    {
        "name": "calculate_obligation",
        "description": (
            "Calculate a PIBO's minimum plastic recycling obligation in kilograms. "
            "Use this whenever a question requires computing an obligation amount. "
            "Do not do the arithmetic yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tonnage":  {"type": "number", "description": "Plastic placed on the market, in tonnes."},
                "category": {"type": "string", "description": "Plastic category: I, II, III, or IV."},
                "year":     {"type": "string", "description": "Financial year, e.g. 2024."},
            },
            "required": ["tonnage", "category", "year"],
        },
    }
]

# --- Piece 2: the dispatcher ---
def run_tool(tool_name, tool_input):
    if tool_name == "calculate_obligation":
        return calculate_obligation(
            tonnage=tool_input["tonnage"],
            category=tool_input["category"],
            year=tool_input["year"],
        )
    raise ValueError(f"Unknown tool: {tool_name}")

# --- Piece 3: the two-call loop ---
def answer_with_tools(question):
    messages = [{"role": "user", "content": question}]

    # CALL 1
    response = client.messages.create(
        model=MODEL, max_tokens=1000, tools=TOOLS, messages=messages,
    )
    print(f"[Call 1 stop_reason: {response.stop_reason}]")

    if response.stop_reason == "tool_use":
        tool_use = next(b for b in response.content if b.type == "tool_use")
        print(f"[Claude asked for: {tool_use.name} with {tool_use.input}]")

        result = run_tool(tool_use.name, tool_use.input)
        print(f"[Our calculator returned: {result} kg]")

        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": str(result),
            }],
        })

        # CALL 2
        response = client.messages.create(
            model=MODEL, max_tokens=1000, tools=TOOLS, messages=messages,
        )

    return response.content[0].text

# --- Runner ---
if __name__ == "__main__":
    q = "A company put 50 tonnes of Category I plastic on the market in 2024. What is its minimum recycling obligation?"
    print(f"\nQuestion: {q}\n")
    answer = answer_with_tools(q)
    print(f"\nClaude's answer:\n{answer}")