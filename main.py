from fastapi import FastAPI
from pydantic import BaseModel
from anthropic import Anthropic
from dotenv import load_dotenv
from cost import query_cost_inr
from calculator import calculate_obligation   # <-- NEW: import the proven function
import chromadb

load_dotenv()

app = FastAPI()
client = Anthropic()

chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection("epr_regulations")

# <-- NEW: the tool schema (the "menu card") and the dispatcher.
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
    if tool_name == "calculate_obligation":
        return calculate_obligation(
            tonnage=tool_input["tonnage"],
            category=tool_input["category"],
            year=tool_input["year"],
        )
    raise ValueError(f"Unknown tool: {tool_name}")


class Question(BaseModel):
    text: str


@app.post("/ask")
def ask(question: Question):
    # 1. RETRIEVE — unchanged.
    results = collection.query(
        query_texts=[question.text],
        n_results=3,
    )
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    # 2. BUILD CONTEXT — unchanged.
    context = ""
    for doc, meta in zip(docs, metas):
        context += f"[Source: {meta['source']}, page {meta['page']}]\n{doc}\n\n"

    # 3. THE RULES — unchanged, but with ONE added sentence about the calculator.
    system_prompt = (
        "You are an EPR compliance assistant. Answer using ONLY the regulation "
        "excerpts provided. Cite the source and page for every fact, like "
        "(EPR Guidelines 2022, page 27). If the excerpts do not contain the answer, "
        "say you don't know — do not guess or use outside knowledge. "
        "If a question requires calculating an obligation amount, use the "
        "calculate_obligation tool — never do the arithmetic yourself."   # <-- NEW sentence
    )

    # 4. ASK CLAUDE — now the back-and-forth lives in a `messages` list we can grow,
    #    and we offer the tool with tools=TOOLS.
    messages = [
        {
            "role": "user",
            "content": f"Regulation excerpts:\n\n{context}\nQuestion: {question.text}",
        }
    ]

    # <-- NEW: track token totals across BOTH calls (was a single call before).
    total_in = 0
    total_out = 0

    # ---- CALL 1 ----
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        tools=TOOLS,                 # <-- NEW: offer the calculator
        messages=messages,
    )
    total_in += response.usage.input_tokens
    total_out += response.usage.output_tokens

    used_tool = False               # <-- NEW: remember whether the calculator ran

    # <-- NEW: the handshake loop — only runs if Claude asked for the tool.
    if response.stop_reason == "tool_use":
        used_tool = True
        tool_use = next(b for b in response.content if b.type == "tool_use")
        result = run_tool(tool_use.name, tool_use.input)

        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": str(result),
            }],
        })

        # ---- CALL 2 ----
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )
        total_in += response.usage.input_tokens
        total_out += response.usage.output_tokens

    # COST — now summed across however many calls happened.
    cost_inr = query_cost_inr(total_in, total_out)
    print(f"[cost] in={total_in}  out={total_out}  tool_used={used_tool}  ≈ ₹{cost_inr:.4f}")

    # 5. RETURN — sources only when no tool was used (a pure-math answer
    #    didn't lean on the chunks, so listing them would be misleading).
    return {
        "answer": response.content[0].text,
        "sources": [] if used_tool else [f"{m['source']} (page {m['page']})" for m in metas],
        "cost_inr": round(cost_inr, 4),
        "tool_used": used_tool,      # <-- NEW: handy for debugging/demo
    }