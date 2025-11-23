"""
Context Extractor for Muze.
Extracts relevant context from user's corpus for AI prompting.
"""

import logging
import re
from google import genai
from google.genai import types
from database import get_user_corpus

logger = logging.getLogger(__name__)


class ContextExtractor:
    def __init__(self, gemini_client):
        self.client = gemini_client

        # Patterns to detect context requests
        self.context_patterns = [
            r'provide\s+(?:me\s+with\s+)?context\s+(?:on|about|regarding|for)\s+(.+)',
            r'give\s+(?:me\s+)?context\s+(?:on|about|regarding|for)\s+(.+)',
            r'context\s+(?:on|about|regarding|for)\s+(.+)',
            r'what\s+do\s+you\s+know\s+about\s+(.+)',
            r'tell\s+me\s+(?:everything\s+)?about\s+(.+)',
        ]

    def is_context_request(self, message: str) -> bool:
        """Check if message is requesting context."""
        message_lower = message.lower().strip()

        for pattern in self.context_patterns:
            if re.search(pattern, message_lower):
                return True

        return False

    def extract_topic(self, message: str) -> str:
        """Extract the topic/subject from context request."""
        message_lower = message.lower().strip()

        for pattern in self.context_patterns:
            match = re.search(pattern, message_lower)
            if match:
                topic = match.group(1).strip()
                # Remove trailing punctuation
                topic = re.sub(r'[.!?]+$', '', topic)
                return topic

        # Fallback: return the whole message
        return message

    def generate_context(self, phone_number: str, topic: str) -> str:
        """
        Generate a detailed, markdown-formatted context prompt about the topic.

        Returns a context prompt ready to be copied and used with other LLMs.
        """
        try:
            # Get user's corpus
            corpus = get_user_corpus(phone_number)

            if not corpus:
                return "❌ No knowledge graph found. Start chatting to build your context library!"

            # Create extraction prompt
            extraction_prompt = f"""You are a context extraction specialist. Your job is to create a detailed, copy-paste ready context prompt from a user's knowledge graph.

**User's Complete Knowledge Graph:**
{corpus}

**Topic/Subject Requested:**
{topic}

**Your Task:**
1. Search the knowledge graph for ALL information related to "{topic}"
2. Extract EVERY relevant detail, fact, relationship, and context
3. Create a comprehensive markdown-formatted context prompt
4. Format it so the user can copy-paste it into another AI (ChatGPT, Claude, etc.)
5. Include:
   - Overview/Summary
   - Key facts and details
   - Related context and background
   - Relevant relationships or connections
   - Any goals, plans, or aspirations related to this topic
6. Make it EXTREMELY detailed but concise
7. **CRITICAL: Keep total length under 1400 characters** (leaves room for user's own prompt)
8. Use markdown formatting: headers, bullet points, bold text

**Output Format:**
```markdown
# Context: [Topic]

## Overview
[Brief summary]

## Key Information
- Detail 1
- Detail 2
- Detail 3

## Additional Context
- Related fact 1
- Related fact 2

## Relevant Details
[Any other important information]
```

**IMPORTANT:**
- If NO information about "{topic}" exists in the knowledge graph, say: "No information about '{topic}' found in your knowledge base yet."
- Be thorough but concise - every word counts
- Make it immediately useful for prompting another AI
- User will paste this directly into another conversation

Generate the context prompt now:"""

            # Call Gemini to extract context
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,  # Balance between creativity and accuracy
                    max_output_tokens=500,  # ~1400 characters max
                )
            )

            context = response.text.strip()

            # Validate length
            if len(context) > 1500:
                # Try to trim while keeping structure
                logger.warning(f"Context too long ({len(context)} chars), trimming...")
                # Keep first 1450 chars and add note
                context = context[:1450] + "\n\n*[Truncated to fit WhatsApp limit]*"

            # Add copy instruction footer
            footer = "\n\n---\n📋 *Copy this message and paste it into your AI conversation for context*"

            if len(context + footer) <= 1550:
                context += footer

            logger.info(f"✅ Context generated for '{topic}' ({len(context)} chars)")
            return context

        except Exception as e:
            logger.error(f"Error generating context: {str(e)}")
            return f"❌ Error generating context: {str(e)}"

    def handle_context_request(self, phone_number: str, message: str) -> tuple[bool, str]:
        """
        Main handler for context requests.

        Returns: (is_context_request: bool, response: str)
        """
        if not self.is_context_request(message):
            return False, ""

        topic = self.extract_topic(message)
        logger.info(f"Context request detected: '{topic}' from {phone_number}")

        context = self.generate_context(phone_number, topic)
        return True, context
