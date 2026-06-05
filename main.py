from fastapi import FastAPI
from pydantic import BaseModel
from anthropic import Anthropic
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()

# Create the FastAPI app and Anthropic client
app = FastAPI()
client = Anthropic()

# This defines the shape of the request body — what JSON we expect
class Question(BaseModel):
    text: str

# This is the endpoint — it listens at POST /ask
@app.post("/ask")
def ask(question: Question):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": question.text}
        ]
    )
    return {"answer": response.content[0].text}