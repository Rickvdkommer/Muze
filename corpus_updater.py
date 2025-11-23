"""
Intelligent corpus updater for Muze.
Automatically extracts insights from conversations and updates user knowledge graphs.
"""

import logging
from google import genai
from google.genai import types
from database import get_user_corpus, update_user_corpus, get_user_messages

logger = logging.getLogger(__name__)


class CorpusUpdater:
    def __init__(self, gemini_client):
        self.client = gemini_client

    def should_update_corpus(self, user_message: str, bot_response: str) -> bool:
        """
        Determine if this conversation contains meaningful information worth storing.
        Uses simple heuristics to avoid unnecessary API calls.
        """
        # Skip very short exchanges
        if len(user_message) < 10:
            return False

        # Skip common greetings/small talk
        small_talk = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'ok', 'okay', 'yes', 'no']
        if user_message.lower().strip() in small_talk:
            return False

        # If message contains personal info markers, update
        personal_markers = [
            'i am', "i'm", 'my', 'i work', 'i like', 'i love', 'i hate',
            'i want', 'i need', 'i think', 'i believe', 'i feel',
            'my family', 'my friend', 'my job', 'my goal'
        ]

        message_lower = user_message.lower()
        for marker in personal_markers:
            if marker in message_lower:
                return True

        # Default: update if message is substantial (>50 chars)
        return len(user_message) > 50

    def update_corpus(self, phone_number: str, user_message: str, bot_response: str = "") -> bool:
        """
        Update user's corpus with insights from the latest conversation.

        Returns True if update was successful, False otherwise.
        """
        try:
            # Check if update is needed
            if not self.should_update_corpus(user_message, bot_response):
                logger.info(f"Skipping corpus update for {phone_number} - no significant info")
                return False

            # Get current corpus
            current_corpus = get_user_corpus(phone_number)
            if not current_corpus:
                logger.warning(f"No corpus found for {phone_number}")
                return False

            # Create extraction prompt (handle case with no bot response yet)
            if bot_response:
                conversation_section = f"""**New Conversation:**
User: {user_message}
Bot: {bot_response}"""
            else:
                conversation_section = f"""**New User Message:**
{user_message}"""

            # Create extraction prompt
            extraction_prompt = f"""You are a personal knowledge curator. Extract meaningful information from this user's message and update their knowledge graph.

**Current Knowledge Graph:**
{current_corpus}

{conversation_section}

**Instructions:**
1. Extract ALL new, meaningful information from the user's message
2. Ignore only obvious small talk or greetings - everything else should be captured
3. Update relevant sections: Worldview, Personal History, Values & Beliefs, Goals & Aspirations, Relationships, Interests & Hobbies, Projects & Work
4. Add new bullet points or expand existing ones
5. If the user mentions projects, products, ideas, or work - capture EVERY detail
6. Preserve all existing information
7. Maintain the markdown structure with section headers
8. Be AGGRESSIVE about capturing information - when in doubt, add it

**Output Rules:**
- Return ONLY the updated markdown knowledge graph
- NO explanations, NO comments, JUST the markdown
- Capture comprehensive details, not just summaries
- Only return unchanged if the message is truly meaningless (greetings, "ok", etc.)

Updated Knowledge Graph:"""

            # Call Gemini to extract and update
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,  # Balanced for comprehensive extraction
                    max_output_tokens=1200,  # Allow for detailed updates
                )
            )

            updated_corpus = response.text.strip()

            # Sanity check: ensure we got valid markdown back
            if not updated_corpus or len(updated_corpus) < 50:
                logger.error("Gemini returned invalid corpus update")
                return False

            # Check if corpus actually changed (avoid unnecessary DB writes)
            if updated_corpus.strip() == current_corpus.strip():
                logger.info(f"No changes to corpus for {phone_number}")
                return True  # Not an error, just no updates needed

            # Update database
            update_user_corpus(phone_number, updated_corpus)
            logger.info(f"✅ Corpus updated for {phone_number}")

            return True

        except Exception as e:
            logger.error(f"Error updating corpus for {phone_number}: {str(e)}")
            return False

    def batch_update_from_recent_messages(self, phone_number: str, message_count: int = 5) -> bool:
        """
        Update corpus from recent unprocessed conversations.
        Useful for catching up on missed updates.
        """
        try:
            messages = get_user_messages(phone_number, limit=message_count)

            if not messages:
                return False

            # Build conversation history
            conversation = []
            for msg in reversed(messages):  # Chronological order
                if msg.direction == 'incoming':
                    conversation.append(f"User: {msg.message_text}")
                else:
                    conversation.append(f"Bot: {msg.message_text}")

            conversation_text = "\n".join(conversation)

            # Get current corpus
            current_corpus = get_user_corpus(phone_number)

            # Create batch update prompt
            batch_prompt = f"""You are a personal knowledge curator. Extract meaningful information from these recent conversations and update the user's knowledge graph.

**Current Knowledge Graph:**
{current_corpus}

**Recent Conversations:**
{conversation_text}

**Instructions:**
1. Extract ALL meaningful information from the conversations
2. Update relevant sections with new insights
3. Keep entries concise and well-organized
4. Preserve all existing information
5. Return ONLY the updated markdown, no explanations

Updated Knowledge Graph:"""

            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=batch_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                )
            )

            updated_corpus = response.text.strip()

            if updated_corpus and len(updated_corpus) > 50:
                update_user_corpus(phone_number, updated_corpus)
                logger.info(f"✅ Batch corpus update completed for {phone_number}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error in batch corpus update: {str(e)}")
            return False
