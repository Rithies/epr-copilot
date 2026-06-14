from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse   # NEW: lets us serve the HTML page
from pydantic import BaseModel
from anthropic import Anthropic
from dotenv import load_dotenv
from cost import query_cost_inr
from calculator import calculate_obligation
from discrepancy import run_all_checks          # NEW: import the proven checks
import chromadb

load_dotenv()

app = FastAPI()
# CORS: tell the browser which origins are allowed to call this API.
# Without this, a page opened from file:// or another domain gets
# "Failed to fetch" — the browser blocks the request before it's sent.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # "*" = allow any origin. Fine for a demo.
    allow_methods=["*"],      # allow POST, GET, etc.
    allow_headers=["*"],      # allow the Content-Type header we send.
)
client = Anthropic()

# -- A: STARTUP ---------------------------------------------------------------
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection("epr_regulations")


# -- B: TOOLS SCHEMA + DISPATCHER ---------------------------------------------
# Two tools now. Claude reads these and decides which (if any) to call.
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
    },
    {
        # NEW TOOL -- the headline capability.
        "name": "check_recycling_claim",
        "description": (
            "Check whether a recycling claim is plausible by running deterministic "
            "discrepancy checks (capacity, material balance, cross-document dates). "
            "Use this whenever the user asks to verify, validate, or assess whether "
            "a recycling claim or certificate is genuine or suspicious. Returns a "
            "structured verdict -- do NOT judge plausibility yourself; rely on the tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "recycler_id":           {"type": "string", "description": "The recycler's ID, e.g. REC-042."},
                "registered_capacity_t": {"type": "number", "description": "Registered/installed capacity in tonnes."},
                "claimed_recycled_t":    {"type": "number", "description": "Tonnes the recycler claims to have recycled."},
                "input_t":               {"type": "number", "description": "Tonnes of waste received as input."},
                "output_t":              {"type": "number", "description": "Tonnes of recyclate produced as output."},
                "cert_year":             {"type": "number", "description": "Year the certificate was issued."},
                "registration_year":    {"type": "number", "description": "Year the recycler was registered."},
            },
            "required": [
                "recycler_id", "registered_capacity_t", "claimed_recycled_t",
                "input_t", "output_t", "cert_year", "registration_year",
            ],
        },
    },
]


def run_tool(tool_name, tool_input):
    """Route Claude's tool request to the real Python function.
    Adding a tool = one more 'if' block. No rewrite."""
    if tool_name == "calculate_obligation":
        return calculate_obligation(
            tonnage=tool_input["tonnage"],
            category=tool_input["category"],
            year=tool_input["year"],
        )
    if tool_name == "check_recycling_claim":        # NEW: route to discrepancy checks
        return run_all_checks(tool_input)            # tool_input IS the claim packet (a dict)
    raise ValueError(f"Unknown tool: {tool_name}")


# -- C: REQUEST MODELS --------------------------------------------------------
class Question(BaseModel):
    text: str


# NEW: the structured claim packet for the production /check-claim door.
# FastAPI validates every field's type before our code ever runs -- if a
# number is missing or the wrong type, the request is rejected automatically.
class ClaimPacket(BaseModel):
    recycler_id: str
    registered_capacity_t: float
    claimed_recycled_t: float
    input_t: float
    output_t: float
    cert_year: int
    registration_year: int


# -- ROOT: SERVE THE UI -------------------------------------------------------
# When someone visits the bare URL (a GET request to "/"), hand the browser
# the index.html page instead of a "Not Found". Because the UI is now served
# by this same app, the page and the API share one origin -- so the browser
# makes no cross-origin call and CORS stops being load-bearing.
@app.get("/")
def home():
    return FileResponse("index.html")


# -- D + E + F: THE ENDPOINT --------------------------------------------------
@app.post("/ask")
def ask(question: Question):

    # D: RETRIEVE -- unchanged.
    results = collection.query(
        query_texts=[question.text],
        n_results=3,
    )
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    context = ""
    for doc, meta in zip(docs, metas):
        context += f"[Source: {meta['source']}, page {meta['page']}]\n{doc}\n\n"

    # Standing rules -- one more sentence about the discrepancy tool.
    system_prompt = (
        "You are an EPR compliance assistant. Answer using ONLY the regulation "
        "excerpts provided. Cite the source and page for every fact, like "
        "(EPR Guidelines 2022, page 27). If the excerpts do not contain the answer, "
        "say you don't know -- do not guess or use outside knowledge. "
        "If a question requires calculating an obligation amount, use the "
        "calculate_obligation tool -- never do the arithmetic yourself. "
        "If the user asks whether a recycling claim is plausible or genuine, use "
        "the check_recycling_claim tool -- never judge plausibility yourself. "
        "When a tool returns a verdict, explain which checks fired and why, in "
        "plain language."
    )

    messages = [
        {
            "role": "user",
            "content": f"Regulation excerpts:\n\n{context}\nQuestion: {question.text}",
        }
    ]

    total_in = 0
    total_out = 0

    # E: AGENT LOOP -- unchanged from Phase 4 Half A.
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
    MAX_LAPS = 5
    laps = 0

    while response.stop_reason == "tool_use" and laps < MAX_LAPS:
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

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )
        total_in  += response.usage.input_tokens
        total_out += response.usage.output_tokens

        laps += 1
        print(f"[agent] lap {laps} done -- stop_reason={response.stop_reason}")

    # F: RETURN -- unchanged.
    cost_inr = query_cost_inr(total_in, total_out)
    print(f"[cost] in={total_in}  out={total_out}  tool_used={used_tool}  laps={laps}  approx Rs {cost_inr:.4f}")

    return {
        "answer":    response.content[0].text,
        "sources":   [] if used_tool else [f"{m['source']} (page {m['page']})" for m in metas],
        "cost_inr":  round(cost_inr, 4),
        "tool_used": used_tool,
    }


# -- G: PRODUCTION DOOR (Option B) --------------------------------------------
# Structured packet in -> deterministic verdict out. Claude is NOT involved.
# This is the trust-boundary-correct path: the flag comes only from code.
@app.post("/check-claim")
def check_claim(packet: ClaimPacket):
    # packet.dict() turns the validated Pydantic model into a plain dict,
    # which is exactly the shape run_all_checks expects.
    verdict = run_all_checks(packet.dict())
    print(f"[check-claim] {verdict['recycler_id']} -> {verdict['status']} {verdict['checks_fired']}")
    return verdict