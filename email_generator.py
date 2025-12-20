from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_available_model():
    """
    Dynamically pick the first available chat-capable model
    to avoid deprecation issues.
    """
    models = client.models.list().data
    for m in models:
        if "chat" in m.id or "instant" in m.id or "versatile" in m.id:
            return m.id
    # fallback to first model if naming changes
    return models[0].id

MODEL_NAME = get_available_model()

def generate_email(purpose, template="professional"):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You write clear, professional business emails."
            },
            {
                "role": "user",
                "content": f"Write a {template} email. {purpose}"
            }
        ],
        temperature=0.4
    )
    return response.choices[0].message.content
