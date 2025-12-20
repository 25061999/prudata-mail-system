import os
from groq import Groq
from dotenv import load_dotenv
import logging

load_dotenv()

# Initialize client with error handling
try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    logging.info("Groq client initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Groq client: {e}")
    client = None

def get_available_model():
    """
    Dynamically pick a model. Includes a fallback to prevent app crash.
    """
    if not client:
        return "llama3-8b-8192"  # Default reliable model if client fails
    try:
        models = client.models.list().data
        for m in models:
            if "chat" in m.id or "instant" in m.id or "versatile" in m.id:
                return m.id
        return models[0].id
    except Exception as e:
        logging.warning(f"Could not fetch model list: {e}. Using default.")
        return "llama3-8b-8192"

MODEL_NAME = get_available_model()

def generate_email(purpose, recipient_name="", template="professional"):
    """
    Generate an email body optimized for inbox deliverability.
    """
    if not client:
        return f"Subject: Regarding {purpose}\n\nDear {recipient_name or 'Team'},\n\nI'm writing to discuss {purpose}. Please let me know your thoughts when you have a moment.\n\nBest,\n[Your Name]"

    # Construct a user prompt that includes the recipient's name if available
    user_content = f"Write a {template} email about: {purpose}"
    if recipient_name:
        user_content += f"\nThe recipient's name is: {recipient_name}"

    # Define the optimized system prompt
    system_prompt = """You are a professional but natural email writer. Write emails that sound like a real person is sending them to a colleague or business contact.

    **CRITICAL GUIDELINES FOR DELIVERABILITY:**
    1. **Tone:** Be conversational, not overly formal or corporate. Avoid phrases like "I hope this email finds you well."
    2. **Structure:** Keep the email concise (max 150-200 words). Use 1-2 short paragraphs instead of long lists of bullet points.
    3. **Personalization:** If a recipient's name is provided, use it naturally at the start.
    4. **Content Focus:** Explain the purpose or benefit to the *recipient*, not just a list of your features.
    5. **Call to Action:** End with a simple, clear, and polite question or next step to encourage a reply.
    6. **Avoid Spam Triggers:** Do NOT use words like "free," "guarantee," "click here," "limited time," or "buy now." Do NOT write in ALL CAPS or use excessive punctuation!!!.
    7. **Placeholders:** Never leave generic placeholders like [Your Website URL]. If a link is needed, simply describe it (e.g., "You can learn more on our website.").
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            temperature=0.6,  # Slightly higher for more natural variation[citation:5]
            max_tokens=400,   # Limits length to prevent overly long emails[citation:5]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"AI email generation failed: {e}")
        # Basic fallback template
        return f"Subject: Regarding {purpose}\n\nDear {recipient_name or 'Team'},\n\nI wanted to connect regarding {purpose}. Would you be available for a brief discussion next week?\n\nBest regards,\n[Your Name]"