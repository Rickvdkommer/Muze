"""
Onboarding State Machine for Muze.
Handles 3-step linear onboarding flow: Name → Location/Timezone → Goals
"""

import logging
from datetime import datetime
from google import genai
from google.genai import types
from database import update_user_field, update_user_onboarding_step, get_user_corpus, update_user_corpus

logger = logging.getLogger(__name__)

# Timezone mapping for common cities (fallback if timezonefinder fails)
TIMEZONE_MAP = {
    # Europe
    'amsterdam': 'Europe/Amsterdam',
    'rotterdam': 'Europe/Amsterdam',
    'utrecht': 'Europe/Amsterdam',
    'the hague': 'Europe/Amsterdam',
    'netherlands': 'Europe/Amsterdam',
    'holland': 'Europe/Amsterdam',
    'london': 'Europe/London',
    'paris': 'Europe/Paris',
    'berlin': 'Europe/Berlin',
    'madrid': 'Europe/Madrid',
    'rome': 'Europe/Rome',
    'barcelona': 'Europe/Madrid',
    'brussels': 'Europe/Brussels',
    'zurich': 'Europe/Zurich',
    'geneva': 'Europe/Zurich',
    'vienna': 'Europe/Vienna',
    'prague': 'Europe/Prague',
    'copenhagen': 'Europe/Copenhagen',
    'stockholm': 'Europe/Stockholm',
    'oslo': 'Europe/Oslo',
    'helsinki': 'Europe/Helsinki',
    'dublin': 'Europe/Dublin',
    'lisbon': 'Europe/Lisbon',
    'athens': 'Europe/Athens',
    'warsaw': 'Europe/Warsaw',
    'budapest': 'Europe/Budapest',

    # North America
    'new york': 'America/New_York',
    'nyc': 'America/New_York',
    'boston': 'America/New_York',
    'miami': 'America/New_York',
    'washington': 'America/New_York',
    'philadelphia': 'America/New_York',
    'los angeles': 'America/Los_Angeles',
    'la': 'America/Los_Angeles',
    'san francisco': 'America/Los_Angeles',
    'sf': 'America/Los_Angeles',
    'seattle': 'America/Los_Angeles',
    'san diego': 'America/Los_Angeles',
    'chicago': 'America/Chicago',
    'denver': 'America/Denver',
    'phoenix': 'America/Phoenix',
    'dallas': 'America/Chicago',
    'houston': 'America/Chicago',
    'atlanta': 'America/New_York',
    'toronto': 'America/Toronto',
    'vancouver': 'America/Vancouver',
    'victoria': 'America/Vancouver',  # BC capital, same timezone as Vancouver
    'montreal': 'America/Montreal',
    'calgary': 'America/Edmonton',
    'edmonton': 'America/Edmonton',

    # Pacific timezone keywords
    'pacific': 'America/Los_Angeles',
    'pst': 'America/Los_Angeles',
    'pdt': 'America/Los_Angeles',
    'pacific time': 'America/Los_Angeles',

    # Asia
    'singapore': 'Asia/Singapore',
    'hong kong': 'Asia/Hong_Kong',
    'tokyo': 'Asia/Tokyo',
    'seoul': 'Asia/Seoul',
    'beijing': 'Asia/Shanghai',
    'shanghai': 'Asia/Shanghai',
    'dubai': 'Asia/Dubai',
    'bangkok': 'Asia/Bangkok',
    'mumbai': 'Asia/Kolkata',
    'delhi': 'Asia/Kolkata',
    'bangalore': 'Asia/Kolkata',
    'manila': 'Asia/Manila',
    'jakarta': 'Asia/Jakarta',
    'kuala lumpur': 'Asia/Kuala_Lumpur',

    # Australia & NZ
    'sydney': 'Australia/Sydney',
    'melbourne': 'Australia/Melbourne',
    'brisbane': 'Australia/Brisbane',
    'perth': 'Australia/Perth',
    'auckland': 'Pacific/Auckland',

    # South America
    'sao paulo': 'America/Sao_Paulo',
    'rio': 'America/Sao_Paulo',
    'buenos aires': 'America/Argentina/Buenos_Aires',
    'santiago': 'America/Santiago',
    'bogota': 'America/Bogota',
    'lima': 'America/Lima',

    # Middle East & Africa
    'tel aviv': 'Asia/Jerusalem',
    'jerusalem': 'Asia/Jerusalem',
    'istanbul': 'Europe/Istanbul',
    'cairo': 'Africa/Cairo',
    'johannesburg': 'Africa/Johannesburg',
    'cape town': 'Africa/Johannesburg',
    'nairobi': 'Africa/Nairobi',
    'lagos': 'Africa/Lagos',
}


class OnboardingManager:
    def __init__(self, gemini_client):
        """
        Initialize onboarding manager with Gemini client.

        Args:
            gemini_client: Initialized Google GenAI client
        """
        self.client = gemini_client

    def parse_timezone(self, location_text: str) -> str:
        """
        Parse timezone from user's location text.

        Args:
            location_text: User input like "Amsterdam", "New York", "PST", "Victoria, Pacific timezone", etc.

        Returns:
            Timezone string (e.g., "Europe/Amsterdam")
        """
        location_lower = location_text.lower().strip()

        # Direct timezone format (e.g., "Europe/Amsterdam")
        if '/' in location_text and len(location_text.split('/')) == 2:
            return location_text

        # Check exact match first
        if location_lower in TIMEZONE_MAP:
            return TIMEZONE_MAP[location_lower]

        # Try matching individual words (handles "Victoria, Pacific timezone" → checks "victoria", "pacific", "timezone")
        words = location_lower.replace(',', ' ').split()
        for word in words:
            if word in TIMEZONE_MAP:
                logger.info(f"Matched timezone keyword '{word}' in '{location_text}'")
                return TIMEZONE_MAP[word]

        # Try partial matches in TIMEZONE_MAP keys (e.g., "SF" matches "san francisco")
        for city, tz in TIMEZONE_MAP.items():
            if location_lower in city or city in location_lower:
                logger.info(f"Partial match: '{location_text}' matched to '{city}'")
                return tz

        # Default fallback
        logger.warning(f"Could not parse timezone from '{location_text}', using default Europe/Amsterdam")
        return 'Europe/Amsterdam'

    def extract_goals_from_text(self, goals_text: str) -> list:
        """
        Use Gemini to extract multiple distinct goals/projects from user text.

        Args:
            goals_text: User's response about their goals

        Returns:
            List of goal dictionaries with name and weight
        """
        extraction_prompt = f"""You are analyzing a user's goals and projects for a personal biographer system.

**User's Input:**
{goals_text}

**Your Task:**
Extract ALL distinct goals, projects, or focus areas mentioned. For each one:
1. Create a clear, concise name (2-5 words)
2. Assign a weight from 1-5 based on:
   - Explicit urgency (5 = "launching next week", 1 = "someday")
   - Level of detail provided (more detail = higher weight)
   - Action-oriented vs aspirational (action = higher weight)

**Output Format:**
Return a JSON array of objects. Each object must have:
- "name": string (the goal/project name)
- "weight": integer 1-5
- "description": string (1 sentence summary)

**Example Output:**
```json
[
  {{"name": "Fundraising for Muze", "weight": 5, "description": "Actively raising seed round"}},
  {{"name": "Health & Fitness", "weight": 3, "description": "General wellness focus"}},
  {{"name": "Shipping MVP", "weight": 4, "description": "Launch product by end of month"}}
]
```

**Rules:**
- Extract AT LEAST 1 goal, even if vague
- If only one thing mentioned, still return it as an array with 1 item
- Don't invent goals not mentioned
- Be generous with weight 4-5 if user seems engaged

Generate the JSON array now:"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=800,
                    response_mime_type="application/json"
                )
            )

            # Parse JSON response
            import json
            goals = json.loads(response.text.strip())

            logger.info(f"Extracted {len(goals)} goals from onboarding")
            return goals

        except Exception as e:
            logger.error(f"Failed to extract goals: {str(e)}")
            # Fallback: create single generic goal
            return [{
                "name": "Personal Development",
                "weight": 3,
                "description": "General life and work goals"
            }]

    def create_open_loops_from_goals(self, goals: list) -> dict:
        """
        Convert extracted goals into open_loops JSON structure.

        Args:
            goals: List of goal dictionaries from extract_goals_from_text

        Returns:
            Dictionary formatted for user.open_loops field
        """
        open_loops = {}
        now = datetime.utcnow().isoformat()

        for goal in goals:
            # Use goal name as key (sanitized)
            key = goal.get('name', 'Unknown Goal')

            open_loops[key] = {
                "status": "active",
                "last_updated": now,
                "next_event_date": None,  # No specific event yet
                "weight": goal.get('weight', 3),
                "description": goal.get('description', '')
            }

        return open_loops

    def handle_onboarding(self, user, incoming_text: str) -> tuple[str, bool]:
        """
        Main onboarding state machine handler.

        Args:
            user: User object from database
            incoming_text: User's message

        Returns:
            Tuple of (response_message, is_complete)
        """
        step = user.onboarding_step
        phone_number = user.phone_number

        logger.info(f"Onboarding step {step} for {phone_number}: {incoming_text[:50]}")

        # Step 0: Ask for name
        if step == 0:
            response = "Hi! I'm Muze, your personal biographer. First, what should I call you?"
            # Move to next step
            update_user_onboarding_step(phone_number, 1)
            return response, False

        # Step 1: Save name, ask for location
        elif step == 1:
            # Save the name
            display_name = incoming_text.strip()
            update_user_field(phone_number, display_name=display_name)

            response = f"Nice to meet you, {display_name}! To ensure I don't message you at inconvenient times, which city or timezone are you in?"

            # Move to next step
            update_user_onboarding_step(phone_number, 2)
            return response, False

        # Step 2: Parse timezone, ask for goals
        elif step == 2:
            # Parse and save timezone
            timezone = self.parse_timezone(incoming_text)
            update_user_field(phone_number, timezone=timezone)

            logger.info(f"Set timezone to {timezone} for {phone_number}")

            response = "Got it. To start, what are the key projects or goals you are focused on right now? Feel free to list a few (e.g., Fundraising, Health, Shipping MVP)."

            # Move to next step
            update_user_onboarding_step(phone_number, 3)
            return response, False

        # Step 3: Extract goals and complete onboarding
        elif step == 3:
            # Extract goals using Gemini
            goals = self.extract_goals_from_text(incoming_text)

            # Convert to open_loops structure
            open_loops = self.create_open_loops_from_goals(goals)

            # Save to database
            update_user_field(phone_number, open_loops=open_loops)

            # Update corpus with goals information
            try:
                corpus = get_user_corpus(phone_number) or ""

                # Build goals section for corpus
                goals_text = "\n".join([
                    f"- **{g.get('name')}** (Priority: {g.get('weight')}/5): {g.get('description', 'No description')}"
                    for g in goals
                ])

                # Add or update Goals & Aspirations section
                if "## Goals & Aspirations" in corpus:
                    # Replace existing section
                    corpus_lines = corpus.split('\n')
                    in_goals_section = False
                    new_corpus_lines = []

                    for line in corpus_lines:
                        if line.startswith('## Goals & Aspirations'):
                            in_goals_section = True
                            new_corpus_lines.append(line)
                            new_corpus_lines.append(goals_text)
                            continue
                        elif in_goals_section and line.startswith('## '):
                            in_goals_section = False
                        elif in_goals_section:
                            continue  # Skip old content

                        new_corpus_lines.append(line)

                    corpus = '\n'.join(new_corpus_lines)
                else:
                    # Add new section
                    corpus += f"\n\n## Goals & Aspirations\n{goals_text}\n"

                update_user_corpus(phone_number, corpus)
                logger.info(f"✅ Updated corpus with {len(goals)} goals for {phone_number}")

            except Exception as e:
                logger.error(f"Failed to update corpus with goals: {str(e)}")

            # Mark onboarding complete
            update_user_onboarding_step(phone_number, 99)

            # Create friendly goal summary
            goal_names = [g.get('name', 'Unknown') for g in goals]
            goal_list = ", ".join(goal_names)

            response = f"Understood. I've noted those priorities: {goal_list}. I'm manually reviewing your background details now to build your base profile. I'll be in touch when there's something relevant to discuss."

            logger.info(f"✅ Onboarding complete for {phone_number} with {len(goals)} goals")
            return response, True

        # Step 99: Already completed (shouldn't reach here)
        else:
            logger.warning(f"Onboarding called for completed user {phone_number}")
            return "You're already onboarded! How can I help?", True
