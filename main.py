from fastapi import FastAPI
from pydantic import BaseModel
from anthropic import Anthropic
from dotenv import load_dotenv
from cost import query_cost_inr
from calculator import calculate_obligation
import chromadb

load_dotenv()

app = FastAPI()
client = Anthropic()

# ── A: STARTUP ────────────────────────────────────────────────────────────────
# Open ChromaDB once at startup, not per request.
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection("epr_regulations")


# ── B: TOOLS SCHEMA + DISPATCHER ─────────────────────────────────────────────
# TOOLS is the "menu card" — the only way Claude learns a tool exists.
# Claude can't see our Python code; this schema is the entire interface.
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


def run_tool(tool_name, tool_input):
    """Route Claude's tool request to the real Python function.
    The name-match is for our code — it's a string comparison, not magic.
    Adding a new tool = one more 'if' block here."""
    if tool_name == "calculate_obligation":
        return calculate_obligation(
            tonnage=tool_input["tonnage"],
            category=tool_input["category"],
            year=tool_input["year"],
        )
    raise ValueError(f"Unknown tool: {tool_name}")


# ── C: REQUEST MODEL ──────────────────────────────────────────────────────────
class Question(BaseModel):
    text: str


# ── D + E + F: THE ENDPOINT ───────────────────────────────────────────────────
@app.post("/ask")
def ask(question: Question):

    # D: RETRIEVE — find the 3 nearest regulation chunks
    results = collection.query(
        query_texts=[question.text],
        n_results=3,
    )
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    # Build the context block Claude will read
    context = ""
    for doc, meta in zip(docs, metas):
        context += f"[Source: {meta['source']}, page {meta['page']}]\n{doc}\n\n"

    # Standing rules — sent every API call (Claude has no memory)
    system_prompt = (
        "You are an EPR compliance assistant. Answer using ONLY the regulation "
        "excerpts provided. Cite the source and page for every fact, like "
        "(EPR Guidelines 2022, page 27). If the excerpts do not contain the answer, "
        "say you don't know — do not guess or use outside knowledge. "
        "If a question requires calculating an obligation amount, use the "
        "calculate_obligation tool — never do the arithmetic yourself."
    )

    # The conversation history — starts with the user's question + chunks.
    # This list grows each agent lap; the full history is resent every call.
    messages = [
        {
            "role": "user",
            "content": f"Regulation excerpts:\n\n{context}\nQuestion: {question.text}",
        }
    ]

    # Token counters — summed across all laps for the true cost
    total_in = 0
    total_out = 0

    # E: AGENT LOOP ─────────────────────────────────────────────────────────
    # Call 1 — always happens. Claude sees question + chunks + tools menu.
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        tools=TOOLS,
        messages=messages,
    )
    total_in  += response.usage.input_tokens
    total_out += response.usage.output_tokens

    used_tool = False

    # Safety cap — never burn more than MAX_LAPS tool calls per request.
    # Without this, a confused model could loop forever and cost a lot.
    MAX_LAPS = 5
    laps = 0

    while response.stop_reason == "tool_use" and laps < MAX_LAPS:
        used_tool = True

        # Find the tool_use block inside Claude's reply
        tool_use = next(b for b in response.content if b.type == "tool_use")
        result = run_tool(tool_use.name, tool_use.input)

        # Grow the messages list.
        # Claude has no memory — we must resend the full history every lap.
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,   # staples result to the request
                "content": str(result),
            }],
        })

        # Next call — resends the whole growing messages list
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )
        total_in  += response.usage.input_tokens
        total_out += response.usage.output_tokens

        laps += 1   # increment AFTER the call; laps = calls made so far
        print(f"[agent] lap {laps} done — stop_reason={response.stop_reason}")

    # Loop exits when stop_reason == "end_turn"  OR  laps hits MAX_LAPS

    # F: RETURN ─────────────────────────────────────────────────────────────
    cost_inr = query_cost_inr(total_in, total_out)
    print(f"[cost] in={total_in}  out={total_out}  tool_used={used_tool}  laps={laps}  ≈ ₹{cost_inr:.4f}")

    return {
        "answer":    response.content[0].text,
        "sources":   [] if used_tool else [f"{m['source']} (page {m['page']})" for m in metas],
        "cost_inr":  round(cost_inr, 4),
        "tool_used": used_tool,
    }