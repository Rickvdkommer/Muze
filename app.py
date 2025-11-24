import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types
from dotenv import load_dotenv
from database import (
    init_db,
    store_message,
    get_user_messages,
    get_user_corpus,
    update_user_corpus,
    get_unprocessed_messages,
    mark_message_processed,
    get_or_create_user,
    get_all_users,
    get_user,
    update_user_interaction
)
from corpus_updater import CorpusUpdater
from context_extractor import ContextExtractor
from audio_transcriber import AudioTranscriber
from onboarding_manager import OnboardingManager
from state_manager import StateManager
from scheduler_dispatcher import SchedulerDispatcher

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for Vercel dashboard
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://www.heymuze.app",
            "https://heymuze.app",
            "https://*.vercel.app",
            "http://localhost:3000"  # For local development
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "whatsapp:+14155238886")

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize Twilio client
from twilio.rest import Client as TwilioClient
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize all AI modules
corpus_updater = CorpusUpdater(client)
context_extractor = ContextExtractor(client)
audio_transcriber = AudioTranscriber(client)
onboarding_manager = OnboardingManager(client)
state_manager = StateManager(client)
scheduler_dispatcher = SchedulerDispatcher(client, twilio_client, TWILIO_PHONE_NUMBER)


# Initialize database on startup
@app.before_request
def before_first_request():
    """Initialize database before first request"""
    if not hasattr(app, 'db_initialized'):
        try:
            init_db()
            app.db_initialized = True
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Twilio webhook endpoint for incoming WhatsApp messages.
    Supports:
    - Onboarding flow (3 steps)
    - Voice message transcription
    - Context requests (auto-respond)
    - Active intelligence (open loops)
    - Human-in-the-loop (admin dashboard)
    """
    try:
        # Get incoming message data
        from_number = request.values.get('From', '')
        incoming_msg = request.values.get('Body', '').strip()
        num_media = int(request.values.get('NumMedia', 0))

        # Ensure user exists in database
        user = get_or_create_user(from_number)

        # Update last_interaction_at for pacing
        update_user_interaction(from_number)

        logger.info(f"Received message from {from_number}: text='{incoming_msg}', media_count={num_media}")

        # Handle voice/audio messages
        if num_media > 0:
            media_url = request.values.get('MediaUrl0', '')
            media_content_type = request.values.get('MediaContentType0', '')

            logger.info(f"Media detected: {media_content_type} at {media_url}")

            # Check if it's an audio file
            if media_content_type and media_content_type.startswith('audio/'):
                try:
                    # Transcribe the voice message
                    transcription = audio_transcriber.process_voice_message(media_url, media_content_type)

                    # Combine transcription with any text caption
                    if incoming_msg:
                        incoming_msg = f"{incoming_msg}\n\n[Voice message transcription]: {transcription}"
                    else:
                        incoming_msg = f"[Voice message]: {transcription}"

                    logger.info(f"Voice message transcribed successfully")

                except Exception as e:
                    logger.error(f"Voice transcription failed: {str(e)}")
                    incoming_msg = incoming_msg or "[Voice message - transcription failed]"
            else:
                logger.info(f"Non-audio media received: {media_content_type} - skipping transcription")

        if not incoming_msg:
            incoming_msg = "[Empty message or unsupported media]"

        # ONBOARDING FLOW: Route through onboarding if not complete
        if user.onboarding_step < 99:
            logger.info(f"User {from_number} in onboarding (step {user.onboarding_step})")

            onboarding_response, is_complete = onboarding_manager.handle_onboarding(user, incoming_msg)

            # Store incoming message and mark as processed (onboarding handled it)
            incoming_message = store_message(from_number, 'incoming', incoming_msg)
            mark_message_processed(incoming_message.id)

            # Store outgoing response
            store_message(from_number, 'outgoing', onboarding_response)

            resp = MessagingResponse()
            resp.message(onboarding_response)

            logger.info(f"Onboarding response sent (step now: {user.onboarding_step})")
            return str(resp)

        # User has completed onboarding - proceed with normal flow

        # Check if this is a context request
        is_context_request, context_response = context_extractor.handle_context_request(
            from_number, incoming_msg
        )

        if is_context_request:
            # Context requests auto-respond immediately
            logger.info(f"Context request detected - auto-responding to {from_number}")

            # Store incoming message
            incoming_message = store_message(
                phone_number=from_number,
                direction='incoming',
                message_text=incoming_msg
            )

            # Store outgoing response
            store_message(
                phone_number=from_number,
                direction='outgoing',
                message_text=context_response
            )

            # Mark incoming message as processed
            mark_message_processed(incoming_message.id)

            # Auto-respond with context
            resp = MessagingResponse()
            resp.message(context_response)

            logger.info(f"Context sent to {from_number}")
            return str(resp)

        # Not a context request - store for human review
        message = store_message(
            phone_number=from_number,
            direction='incoming',
            message_text=incoming_msg
        )

        logger.info(f"Message stored with ID: {message.id} - awaiting human review")

        # ACTIVE INTELLIGENCE: Update corpus + open loops
        try:
            # Get current state
            corpus = get_user_corpus(from_number) or ""
            current_loops = user.open_loops or {}

            # Update corpus (extract new information)
            corpus_updater.update_corpus(from_number, incoming_msg, "")
            logger.info(f"Corpus update triggered for {from_number}")

            # Update open loops (detect events, close loops, detect decay)
            updated_loops, cleanup_instructions = state_manager.update_open_loops(
                from_number,
                corpus,
                incoming_msg,
                current_loops
            )

            # Apply corpus cleanup if needed (Gardener Rule)
            if cleanup_instructions:
                updated_corpus = get_user_corpus(from_number)
                cleaned_corpus = state_manager.apply_corpus_cleanup(
                    from_number,
                    updated_corpus,
                    cleanup_instructions
                )
                update_user_corpus(from_number, cleaned_corpus)
                logger.info(f"Applied {len(cleanup_instructions)} corpus cleanup actions")

        except Exception as e:
            logger.error(f"Active intelligence update failed (non-critical): {str(e)}")

        # Return empty response (human-in-the-loop)
        resp = MessagingResponse()
        return str(resp)

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        resp = MessagingResponse()
        return str(resp)


@app.route("/api/users", methods=["GET"])
def list_users():
    """
    Get all users who have messaged the bot.
    Example: /api/users
    """
    try:
        users = get_all_users()

        return jsonify({
            "count": len(users),
            "users": [
                {
                    "phone_number": user.phone_number,
                    "display_name": user.display_name,
                    "created_at": user.created_at.isoformat(),
                    "last_message_at": user.last_message_at.isoformat()
                }
                for user in users
            ]
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<phone_number>/messages", methods=["GET"])
def get_messages(phone_number):
    """
    Get message history for a specific user.
    Example: /api/users/whatsapp:+31634829116/messages?limit=50
    """
    try:
        limit = request.args.get('limit', 50, type=int)

        # Add whatsapp: prefix if not present
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'

        messages = get_user_messages(phone_number, limit=limit)

        return jsonify({
            "phone_number": phone_number,
            "message_count": len(messages),
            "messages": [
                {
                    "id": msg.id,
                    "direction": msg.direction,
                    "text": msg.message_text,
                    "timestamp": msg.timestamp.isoformat(),
                    "processed": msg.processed
                }
                for msg in messages
            ]
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving messages: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<phone_number>/corpus", methods=["GET"])
def get_corpus(phone_number):
    """
    Get the markdown corpus for a specific user.
    Example: /api/users/whatsapp:+31634829116/corpus
    """
    try:
        # Add whatsapp: prefix if not present
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'

        corpus = get_user_corpus(phone_number)

        if corpus:
            return jsonify({
                "phone_number": phone_number,
                "corpus": corpus
            }), 200
        else:
            return jsonify({
                "error": "User not found or corpus not available"
            }), 404

    except Exception as e:
        logger.error(f"Error retrieving corpus: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<phone_number>/corpus", methods=["PUT"])
def update_corpus(phone_number):
    """
    Update the corpus for a specific user.
    Example: PUT /api/users/whatsapp:+31634829116/corpus
    Body: {"corpus": "# Updated corpus..."}
    """
    try:
        # Add whatsapp: prefix if not present
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'

        data = request.get_json()
        new_corpus = data.get('corpus')

        if not new_corpus:
            return jsonify({"error": "corpus field required"}), 400

        success = update_user_corpus(phone_number, new_corpus)

        if success:
            return jsonify({
                "message": "Corpus updated successfully",
                "phone_number": phone_number
            }), 200
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        logger.error(f"Error updating corpus: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/messages/unprocessed", methods=["GET"])
def get_unprocessed():
    """
    Get unprocessed messages (for human-in-the-loop queue).
    Example: /api/messages/unprocessed?limit=10
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        messages = get_unprocessed_messages(limit=limit)

        return jsonify({
            "count": len(messages),
            "messages": [
                {
                    "id": msg.id,
                    "phone_number": msg.phone_number,
                    "text": msg.message_text,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving unprocessed messages: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/messages/<int:message_id>/process", methods=["POST"])
def process_message(message_id):
    """
    Mark a message as processed.
    Example: POST /api/messages/123/process
    """
    try:
        success = mark_message_processed(message_id)

        if success:
            return jsonify({
                "message": "Message marked as processed",
                "message_id": message_id
            }), 200
        else:
            return jsonify({"error": "Message not found"}), 404

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-response", methods=["POST"])
def generate_response():
    """
    Generate AI response for a given message (to be used by human reviewer).
    Example: POST /api/generate-response
    Body: {"phone_number": "whatsapp:+31...", "message": "user message"}
    """
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        user_message = data.get('message')

        if not phone_number or not user_message:
            return jsonify({"error": "phone_number and message required"}), 400

        # Check if this is a context request
        is_context_request, context_response = context_extractor.handle_context_request(
            phone_number, user_message
        )

        # If it's a context request, return the context
        if is_context_request:
            return jsonify({
                "response": context_response,
                "phone_number": phone_number
            }), 200

        # Otherwise, generate normal Muze response
        # Get user's corpus
        corpus = get_user_corpus(phone_number) or "No information yet."

        # System prompt defining Muze's persona
        system_prompt = f"""You are Muze, a personal biographer AI assistant. Your purpose is to understand the user deeply by engaging in meaningful conversations.

**Your Personality:**
- Inquisitive: You're genuinely curious about the user's life, thoughts, and experiences
- Succinct: You keep responses VERY brief (1-2 sentences max, under 200 characters if possible)
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
                max_output_tokens=120,  # Reduced to ensure under 1600 char WhatsApp limit
            )
        )

        ai_response = response.text.strip()

        return jsonify({
            "response": ai_response,
            "phone_number": phone_number
        }), 200

    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/update-corpus", methods=["POST"])
def update_corpus_endpoint():
    """
    Update user's corpus after a conversation exchange.
    Example: POST /api/update-corpus
    Body: {"phone_number": "whatsapp:+31...", "user_message": "...", "bot_response": "..."}
    """
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        user_message = data.get('user_message')
        bot_response = data.get('bot_response', '')  # Optional, defaults to empty string

        if not phone_number or not user_message:
            return jsonify({"error": "phone_number and user_message required"}), 400

        # Update corpus using the intelligent updater
        success = corpus_updater.update_corpus(phone_number, user_message, bot_response)

        if success:
            return jsonify({
                "message": "Corpus updated successfully",
                "phone_number": phone_number
            }), 200
        else:
            return jsonify({
                "message": "No updates needed or update skipped",
                "phone_number": phone_number
            }), 200

    except Exception as e:
        logger.error(f"Error in corpus update endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/cron/process-nudges", methods=["POST"])
def process_nudges():
    """
    Cron endpoint for proactive nudges (Scheduler Dispatcher).
    Should be called by an external cron service (e.g., cron-job.org, Railway Cron).

    Security: Add authentication header check in production.
    """
    try:
        logger.info("=== CRON: Process Nudges Triggered ===")

        # Security check: Verify cron secret token
        auth_token = request.headers.get('X-Cron-Secret')
        expected_token = os.getenv('CRON_SECRET_TOKEN')

        if expected_token and auth_token != expected_token:
            logger.warning("⚠️ Unauthorized cron attempt - invalid token")
            return jsonify({"error": "Unauthorized"}), 401

        # Run dispatcher
        result = scheduler_dispatcher.process_dispatch_queue()

        logger.info(f"=== CRON: Complete - Sent {result['sent']}, Skipped {result['skipped']} ===")

        return jsonify({
            "status": "success",
            "sent": result['sent'],
            "skipped": result['skipped']
        }), 200

    except Exception as e:
        logger.error(f"Error in cron endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<phone_number>/details", methods=["GET"])
def get_user_details(phone_number):
    """
    Get complete user details including settings and open loops.
    Example: GET /api/users/whatsapp:+31634829116/details
    """
    try:
        # Add whatsapp: prefix if not present
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'

        from database import get_user
        user = get_user(phone_number)

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "phone_number": user.phone_number,
            "display_name": user.display_name,
            "created_at": user.created_at.isoformat(),
            "last_message_at": user.last_message_at.isoformat(),
            "last_interaction_at": user.last_interaction_at.isoformat() if user.last_interaction_at else None,
            "timezone": user.timezone,
            "quiet_hours_start": user.quiet_hours_start,
            "quiet_hours_end": user.quiet_hours_end,
            "onboarding_step": user.onboarding_step,
            "open_loops": user.open_loops,
            "pending_questions": user.pending_questions
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving user details: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<phone_number>/settings", methods=["PUT"])
def update_user_settings(phone_number):
    """
    Update user settings (timezone, quiet hours, etc.).
    Example: PUT /api/users/whatsapp:+31634829116/settings
    Body: {"timezone": "America/New_York", "quiet_hours_start": 23, ...}
    """
    try:
        # Add whatsapp: prefix if not present
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'

        data = request.get_json()

        from database import update_user_field
        success = update_user_field(phone_number, **data)

        if success:
            return jsonify({
                "message": "Settings updated successfully",
                "phone_number": phone_number
            }), 200
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        logger.error(f"Error updating user settings: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<phone_number>/reset-corpus", methods=["POST"])
def reset_user_corpus(phone_number):
    """
    Reset user's corpus to default template.
    Example: POST /api/users/whatsapp:+31634829116/reset-corpus
    """
    try:
        # Add whatsapp: prefix if not present
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'

        from database import get_user
        from datetime import datetime

        user = get_user(phone_number)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Create fresh corpus template
        fresh_corpus = f"""# Personal Knowledge Graph - {user.display_name or phone_number}

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

## Projects & Work
_No information yet._

---
_Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_
"""

        success = update_user_corpus(phone_number, fresh_corpus)

        if success:
            logger.info(f"✅ Corpus reset for {phone_number}")
            return jsonify({
                "message": "Corpus reset successfully",
                "phone_number": phone_number
            }), 200
        else:
            return jsonify({"error": "Failed to reset corpus"}), 500

    except Exception as e:
        logger.error(f"Error resetting corpus: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<phone_number>/messages", methods=["DELETE"])
def delete_user_messages(phone_number):
    """
    Delete all messages for a user.
    Example: DELETE /api/users/whatsapp:+31634829116/messages
    """
    try:
        # Add whatsapp: prefix if not present
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'

        from database import get_db
        from database import Message

        db = get_db()
        try:
            count = db.query(Message).filter(Message.phone_number == phone_number).delete()
            db.commit()

            logger.info(f"✅ Deleted {count} messages for {phone_number}")

            return jsonify({
                "message": f"Deleted {count} messages",
                "phone_number": phone_number,
                "count": count
            }), 200

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error deleting messages: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "service": "muze-biographer"}, 200


@app.route("/", methods=["GET"])
def home():
    """Root endpoint."""
    return {
        "message": "Muze Personal Biographer API - Active Intelligence Edition",
        "status": "running",
        "version": "2.0.0",
        "features": [
            "Onboarding State Machine (3 steps)",
            "Open Loop Tracking (future events, decaying topics)",
            "Smart Dispatcher (proactive nudges)",
            "Voice Message Transcription",
            "Context Extraction",
            "Human-in-the-Loop Dashboard"
        ],
        "endpoints": {
            "webhook": "/webhook (POST)",
            "cron_nudges": "/api/cron/process-nudges (POST)",
            "get_messages": "/api/users/<phone_number>/messages (GET)",
            "get_corpus": "/api/users/<phone_number>/corpus (GET)",
            "update_corpus": "/api/users/<phone_number>/corpus (PUT)",
            "unprocessed_messages": "/api/messages/unprocessed (GET)",
            "process_message": "/api/messages/<id>/process (POST)",
            "generate_response": "/api/generate-response (POST)",
            "health": "/health (GET)"
        }
    }, 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
