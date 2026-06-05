from anthropic import Anthropic
from dotenv import load_dotenv

# Load the API key from .env file
load_dotenv()

# Create a client — this is your "connection" to Claude
client = Anthropic()

# Send a question and get an answer
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "What is Extended Producer Responsibility (EPR) in India, in 2 sentences?"}
    ]
)

# Print the answer
print(response.content[0].text)