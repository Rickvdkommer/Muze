import os
import logging
from pathlib import Path
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
CORPUS_FILE = "user_corpus.md"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


def load_corpus():
    """Load the user corpus from the markdown file."""
    corpus_path = Path(CORPUS_FILE)
    if corpus_path.exists():
        with open(corpus_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        # Create initial corpus structure
        initial_corpus = """# Personal Knowledge Graph

## Worldview
_No information yet._

## Personal History
_No information yet._

## Values & Beliefs
_No information yet._

## Goals & Aspirations
_No information yet._

## Relationships
_No information yet._

## Interests & Hobbies
_No information yet._

---
_Last updated: Initial creation_
"""
        with open(corpus_path, 'w', encoding='utf-8') as f:
            f.write(initial_corpus)
        return initial_corpus


def update_corpus(user_message, ai_response):
    """
    Update the corpus with new conversation insights using Gemini to organize content.
    """
    try:
        current_corpus = load_corpus()

        # Create prompt for Gemini to refine and update the corpus
        refine_prompt = f"""You are a personal knowledge curator. Your job is to update a structured knowledge graph about a person based on new conversation information.

**Current Knowledge Graph:**
{current_corpus}

**New Conversation:**
User: {user_message}
AI: {ai_response}

**Task:**
1. Extract any meaningful information about the user from this conversation
2. Update the relevant sections of the knowledge graph (Worldview, Personal History, Values & Beliefs, Goals & Aspirations, Relationships, Interests & Hobbies)
3. Preserve all existing information
4. Add new insights in a concise, organized manner
5. If no new information is worth adding, return the corpus unchanged
6. Keep the markdown structure intact

Return ONLY the updated knowledge graph in markdown format, nothing else."""

        # Use Gemini to refine the corpus
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=refine_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2000,
            )
        )

        refined_corpus = response.text.strip()

        # Save updated corpus
        with open(CORPUS_FILE, 'w', encoding='utf-8') as f:
            f.write(refined_corpus)

        logger.info("Corpus updated successfully")

    except Exception as e:
        logger.error(f"Error updating corpus: {str(e)}")


def generate_ai_response(user_message):
    """
    Generate an AI response using Gemini with the current corpus as context.
    """
    try:
        corpus = load_corpus()

        # System prompt defining Muze's persona
        system_prompt = f"""You are Muze, a personal biographer AI assistant. Your purpose is to understand the user deeply by engaging in meaningful conversations.

**Your Personality:**
- Inquisitive: You're genuinely curious about the user's life, thoughts, and experiences
- Succinct: You keep responses brief and to the point (2-3 sentences max)
- Empathetic: You understand and validate emotions
- Thoughtful: You ask one insightful follow-up question to dig deeper

**Your Knowledge About the User:**
{corpus}

**Conversation Rules:**
1. Always acknowledge what the user shared
2. Show genuine interest and empathy
3. Ask ONE specific follow-up question to learn more
4. Build on previous knowledge when relevant
5. Be conversational, not formal
6. Never ask multiple questions at once

**Current Message from User:**
{user_message}

Respond naturally and ask one thoughtful follow-up question."""

        # Generate response with Gemini
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=system_prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=200,
            )
        )

        ai_response = response.text.strip()

        # Update corpus asynchronously (in production, use a task queue)
        update_corpus(user_message, ai_response)

        return ai_response

    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return "I'm having trouble processing that right now. Could you try again?"


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Twilio webhook endpoint for incoming WhatsApp messages.
    """
    try:
        # Get incoming message
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')

        logger.info(f"Received message from {from_number}: {incoming_msg}")

        # Generate AI response
        ai_response = generate_ai_response(incoming_msg)

        # Create Twilio response
        resp = MessagingResponse()
        resp.message(ai_response)

        logger.info(f"Sending response: {ai_response}")

        return str(resp)

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        resp = MessagingResponse()
        resp.message("Sorry, something went wrong. Please try again.")
        return str(resp)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "service": "muze-biographer"}, 200


@app.route("/", methods=["GET"])
def home():
    """Root endpoint."""
    return {"message": "Muze Personal Biographer API", "status": "running"}, 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
