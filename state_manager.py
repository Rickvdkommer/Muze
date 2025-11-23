"""
State Manager - The Brain of Muze's Active Intelligence.
Tracks "Open Loops" (future events, ongoing projects, decaying topics).
Implements the "Gardener Rule" to keep the corpus clean and relevant.
"""

import logging
import json
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from database import update_user_field, get_user_corpus

logger = logging.getLogger(__name__)


class StateManager:
    def __init__(self, gemini_client):
        """
        Initialize state manager with Gemini client.

        Args:
            gemini_client: Initialized Google GenAI client
        """
        self.client = gemini_client

    def update_open_loops(
        self,
        phone_number: str,
        user_corpus: str,
        incoming_message: str,
        current_loops: dict
    ) -> tuple[dict, list]:
        """
        Analyze conversation and update open loops.
        This is the core intelligence that:
        1. Detects new future events → Add to loops
        2. Detects completed tasks → Close loops
        3. Detects decaying topics → Flag for follow-up
        4. Identifies obsolete corpus lines → Gardener cleanup

        Args:
            phone_number: User's phone number
            user_corpus: Current markdown knowledge graph
            incoming_message: Latest message from user
            current_loops: Current open_loops JSON

        Returns:
            Tuple of (updated_loops_dict, corpus_cleanup_instructions)
        """

        # Prepare current loops summary for Gemini
        loops_summary = json.dumps(current_loops, indent=2) if current_loops else "{}"

        analysis_prompt = f"""You are the State Manager for Muze, a personal biographer system.
Your job is to analyze the user's latest message and manage their "Open Loops" - ongoing projects, future events, and topics that need follow-up.

**User's Knowledge Graph:**
{user_corpus}

**Current Open Loops:**
```json
{loops_summary}
```

**Latest User Message:**
"{incoming_message}"

**Your Tasks:**

1. **Detect New Loops:**
   - Did the user mention a FUTURE EVENT? (e.g., "Pitching on Friday", "Meeting next week", "Launch in 2 weeks")
   - Did they introduce a NEW PROJECT or GOAL?
   - If yes, add it to the loops with:
     - Key: Short descriptive name
     - status: "active"
     - last_updated: Current ISO timestamp
     - next_event_date: ISO date if specific, otherwise null
     - weight: 5 if urgent/time-bound, 3-4 if important, 1-2 if mentioned casually
     - description: 1 sentence summary

2. **Close Completed Loops:**
   - Did the user indicate something is DONE? (e.g., "Pitch went great", "Shipped the MVP", "Completed X")
   - If yes, mark those loops with status: "resolved" OR remove them entirely

3. **Detect Decay:**
   - Check `last_updated` timestamps in current loops
   - If a loop hasn't been mentioned in over 7 days AND still marked "active", flag it by:
     - Setting status: "decaying"
     - Keeping the weight the same
   - These will trigger check-in questions later

4. **Gardener Rule (Corpus Cleanup):**
   - Identify OBSOLETE or OUTDATED lines in the knowledge graph
   - Examples:
     - "Currently raising seed round" → but they just got funding
     - "Shipping MVP by March" → but it's now June
     - Contradictory information (old vs new)
   - Return a list of corpus cleanup instructions

**Output Format:**
Return JSON with this exact structure:

```json
{{
  "updated_loops": {{
    "Topic Name": {{
      "status": "active|decaying|resolved",
      "last_updated": "2025-01-23T20:00:00",
      "next_event_date": "2025-01-25" or null,
      "weight": 1-5,
      "description": "Brief description"
    }}
  }},
  "corpus_cleanup": [
    "DELETE line: 'Currently raising seed round' - they secured funding",
    "REPLACE 'Shipping MVP by March' with 'Shipped MVP in March 2025'"
  ],
  "reasoning": "Brief explanation of changes made"
}}
```

**Important Rules:**
- PRESERVE all loops that are still relevant
- Only mark as "resolved" if user explicitly completed it
- Be conservative with decay - wait for 7+ days
- Corpus cleanup should be SPECIFIC - exact text to delete/replace
- If no changes needed, return empty arrays/objects
- Today's date: {datetime.utcnow().strftime('%Y-%m-%d')}

Analyze and generate the JSON now:"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=analysis_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=1500,
                    response_mime_type="application/json"
                )
            )

            # Parse JSON response
            result = json.loads(response.text.strip())

            updated_loops = result.get('updated_loops', {})
            corpus_cleanup = result.get('corpus_cleanup', [])
            reasoning = result.get('reasoning', '')

            logger.info(f"State update for {phone_number}: {reasoning}")
            logger.info(f"Loop changes: {len(updated_loops)} total, {len(corpus_cleanup)} cleanup items")

            # Save updated loops to database
            if updated_loops:
                update_user_field(phone_number, open_loops=updated_loops)

            return updated_loops, corpus_cleanup

        except Exception as e:
            logger.error(f"Failed to update open loops: {str(e)}")
            # Fallback: just update timestamp on existing loops
            now = datetime.utcnow().isoformat()
            fallback_loops = current_loops.copy()
            for key in fallback_loops:
                if fallback_loops[key].get('status') == 'active':
                    fallback_loops[key]['last_updated'] = now

            return fallback_loops, []

    def apply_corpus_cleanup(
        self,
        phone_number: str,
        current_corpus: str,
        cleanup_instructions: list
    ) -> str:
        """
        Apply Gardener Rule cleanup instructions to corpus.

        Args:
            phone_number: User's phone number
            current_corpus: Current markdown corpus
            cleanup_instructions: List of cleanup actions from update_open_loops

        Returns:
            Cleaned corpus markdown
        """
        if not cleanup_instructions:
            return current_corpus

        logger.info(f"Applying {len(cleanup_instructions)} corpus cleanup actions for {phone_number}")

        # Use Gemini to apply cleanup intelligently
        cleanup_prompt = f"""You are maintaining a personal knowledge graph. Apply the following cleanup instructions:

**Current Corpus:**
{current_corpus}

**Cleanup Instructions:**
{chr(10).join(f"- {instruction}" for instruction in cleanup_instructions)}

**Your Task:**
Apply these cleanup instructions to the corpus:
- DELETE outdated or contradictory information
- REPLACE with updated information where specified
- PRESERVE all other content exactly as-is
- Maintain markdown formatting and structure

**Output:**
Return ONLY the cleaned corpus markdown. No explanations, no comments.

Cleaned corpus:"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=cleanup_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2000,
                )
            )

            cleaned_corpus = response.text.strip()

            # Sanity check: ensure we got valid markdown back
            if len(cleaned_corpus) < 50:
                logger.error("Gemini returned invalid corpus after cleanup, keeping original")
                return current_corpus

            logger.info(f"✅ Corpus cleaned for {phone_number}")
            return cleaned_corpus

        except Exception as e:
            logger.error(f"Failed to apply corpus cleanup: {str(e)}")
            return current_corpus

    def detect_decaying_loops(self, open_loops: dict, days_threshold: int = 7) -> list:
        """
        Find loops that haven't been updated in N days.

        Args:
            open_loops: User's current open_loops dict
            days_threshold: Number of days before considering a loop "decaying"

        Returns:
            List of loop names that are decaying
        """
        decaying = []
        now = datetime.utcnow()

        for topic, data in open_loops.items():
            if data.get('status') != 'active':
                continue  # Skip resolved or already flagged loops

            last_updated_str = data.get('last_updated')
            if not last_updated_str:
                continue

            try:
                last_updated = datetime.fromisoformat(last_updated_str)
                days_since = (now - last_updated).days

                if days_since >= days_threshold:
                    decaying.append(topic)
                    logger.info(f"Loop '{topic}' decaying: {days_since} days since update")

            except Exception as e:
                logger.error(f"Error parsing date for loop '{topic}': {e}")

        return decaying

    def get_upcoming_events(self, open_loops: dict, days_ahead: int = 7) -> list:
        """
        Find loops with events happening soon.

        Args:
            open_loops: User's current open_loops dict
            days_ahead: Look ahead N days for upcoming events

        Returns:
            List of (topic_name, event_date, days_until) tuples
        """
        upcoming = []
        now = datetime.utcnow()

        for topic, data in open_loops.items():
            event_date_str = data.get('next_event_date')
            if not event_date_str or data.get('status') != 'active':
                continue

            try:
                event_date = datetime.fromisoformat(event_date_str)
                days_until = (event_date - now).days

                # Event is within the next N days
                if 0 <= days_until <= days_ahead:
                    upcoming.append((topic, event_date_str, days_until))
                    logger.info(f"Upcoming event: '{topic}' in {days_until} days")

            except Exception as e:
                logger.error(f"Error parsing event date for '{topic}': {e}")

        return sorted(upcoming, key=lambda x: x[2])  # Sort by days_until

    def generate_check_in_question(
        self,
        topic: str,
        loop_data: dict,
        corpus_context: str
    ) -> str:
        """
        Generate a natural check-in question for a specific loop.

        Args:
            topic: The loop/topic name
            loop_data: The loop's data dict (status, weight, description, etc.)
            corpus_context: Relevant corpus excerpt for context

        Returns:
            Natural, personalized check-in question
        """
        status = loop_data.get('status', 'active')
        weight = loop_data.get('weight', 3)
        description = loop_data.get('description', '')
        next_event = loop_data.get('next_event_date')

        question_prompt = f"""Generate a natural, personalized check-in question for a user.

**Topic:** {topic}
**Status:** {status}
**Weight (urgency):** {weight}/5
**Description:** {description}
**Upcoming Event:** {next_event if next_event else 'None'}

**Context from Knowledge Graph:**
{corpus_context[:500]}

**Your Task:**
Create a brief (1-2 sentence), natural question that:
- Feels like a genuine check-in from a friend
- References specific context if available
- Is appropriately urgent based on weight (5 = "How did X go?", 1 = "Any updates on Y?")
- Doesn't feel robotic or formulaic

**Examples:**
- "Hey! You mentioned pitching to investors this week - how did that go?"
- "It's been a bit - any progress on the MVP launch?"
- "Just checking in on your health goals. How's it going?"

Generate the question now (just the question, nothing else):"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=question_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=100,
                )
            )

            question = response.text.strip()
            return question

        except Exception as e:
            logger.error(f"Failed to generate check-in question: {str(e)}")
            # Fallback generic question
            return f"Hey! Any updates on {topic}?"
