from fastapi import FastAPI
from pydantic import BaseModel
from anthropic import Anthropic
from dotenv import load_dotenv
import chromadb

# Load API key from .env
load_dotenv()

# Create the FastAPI app and Anthropic client
app = FastAPI()
client = Anthropic()

# Open the vector store ONCE, when the server starts up.
# Opening it on every request would be slow — load it once, reuse it for all questions.
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection("epr_regulations")

# This defines the shape of the request body — what JSON we expect
class Question(BaseModel):
    text: str

# This is the endpoint — it listens at POST /ask
@app.post("/ask")
def ask(question: Question):
    # 1. RETRIEVE — find the 3 nearest chunks (the teal box from the diagram).
    results = collection.query(
        query_texts=[question.text],
        n_results=3,
    )
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    # 2. BUILD CONTEXT — stitch the chunks into one labelled block so Claude
    #    sees both the text AND where each piece came from (for citations).
    context = ""
    for doc, meta in zip(docs, metas):
        context += f"[Source: {meta['source']}, page {meta['page']}]\n{doc}\n\n"

    # 3. THE RULES — cite-or-refuse. This is the trust boundary, written in English.
    system_prompt = (
        "You are an EPR compliance assistant. Answer using ONLY the regulation "
        "excerpts provided. Cite the source and page for every fact, like "
        "(EPR Guidelines 2022, page 27). If the excerpts do not contain the answer, "
        "say you don't know — do not guess or use outside knowledge."
    )

    # 4. ASK CLAUDE — hand it the chunks + the question.
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Regulation excerpts:\n\n{context}\nQuestion: {question.text}",
            }
        ],
    )

    # 5. RETURN — the answer plus which chunks we used (proof, and handy for debugging).
    return {
        "answer": response.content[0].text,
        "sources": [f"{m['source']} (page {m['page']})" for m in metas],
    }