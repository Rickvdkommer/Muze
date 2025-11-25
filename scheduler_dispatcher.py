"""
Scheduler Dispatcher - The Nudge Engine.
Proactively reaches out to users based on:
- Upcoming events (next_event_date)
- Decaying topics (7+ days without update)
- Smart pacing rules (weight-based timing)
- Quiet hours respect (timezone-aware)
- Ghost loop prevention (avoid redundant questions)
"""

import logging
from datetime import datetime, timedelta
import pytz
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

from database import (
    get_users_for_dispatch,
    get_user_messages,
    get_user_corpus,
    update_user_field,
    store_message,
    update_user_interaction,
    create_pending_nudge,
    check_existing_pending_nudge
)
from state_manager import StateManager

logger = logging.getLogger(__name__)


class SchedulerDispatcher:
    def __init__(
        self,
        gemini_client,
        twilio_client,
        twilio_phone_number: str
    ):
        """
        Initialize scheduler dispatcher.

        Args:
            gemini_client: Initialized Google GenAI client
            twilio_client: Initialized Twilio client
            twilio_phone_number: Twilio WhatsApp number (e.g., "whatsapp:+14155238886")
        """
        self.client = gemini_client
        self.twilio = twilio_client
        self.from_number = twilio_phone_number
        self.state_manager = StateManager(gemini_client)

    def is_quiet_hours(self, user) -> bool:
        """
        Check if current time is within user's quiet hours.

        Args:
            user: User object with timezone and quiet_hours settings

        Returns:
            True if currently in quiet hours, False otherwise
        """
        try:
            # Get user's current time
            user_tz = pytz.timezone(user.timezone)
            current_time_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
            current_time_user = current_time_utc.astimezone(user_tz)

            current_hour = current_time_user.hour

            quiet_start = user.quiet_hours_start
            quiet_end = user.quiet_hours_end

            # Handle overnight quiet hours (e.g., 22:00 to 09:00)
            if quiet_start > quiet_end:
                # Quiet hours span midnight
                is_quiet = current_hour >= quiet_start or current_hour < quiet_end
            else:
                # Normal quiet hours within same day
                is_quiet = quiet_start <= current_hour < quiet_end

            if is_quiet:
                logger.info(f"User {user.phone_number} in quiet hours ({quiet_start}-{quiet_end})")

            return is_quiet

        except Exception as e:
            logger.error(f"Error checking quiet hours for {user.phone_number}: {e}")
            return True  # Err on side of caution

    def should_send_based_on_pacing(self, user, weight: int) -> bool:
        """
        Determine if enough time has passed to send a message based on weight.

        Pacing Rules:
        - Weight 5 (High Priority): Send if 4+ hours since last interaction
        - Weight 3-4 (Medium): Send if 24+ hours since last interaction
        - Weight 1-2 (Low): Send if 48+ hours since last interaction

        Args:
            user: User object
            weight: Question weight (1-5)

        Returns:
            True if pacing allows sending, False otherwise
        """
        if not user.last_interaction_at:
            # No previous interaction, OK to send
            return True

        now = datetime.utcnow()
        time_since_last = now - user.last_interaction_at
        hours_since = time_since_last.total_seconds() / 3600

        # Pacing thresholds
        if weight >= 5:
            threshold = 4  # hours
        elif weight >= 3:
            threshold = 24  # hours
        else:
            threshold = 48  # hours

        can_send = hours_since >= threshold

        if not can_send:
            logger.info(
                f"Pacing block for {user.phone_number}: "
                f"{hours_since:.1f}h since last, need {threshold}h (weight={weight})"
            )

        return can_send

    def check_ghost_loops(self, user, topic: str) -> bool:
        """
        Check if topic was recently discussed (Ghost Loop Prevention).

        Args:
            user: User object
            topic: Topic/loop name to check

        Returns:
            True if topic is a "ghost" (recently discussed), False if safe
        """
        # Get last 3 messages
        recent_messages = get_user_messages(user.phone_number, limit=3)

        for msg in recent_messages:
            # Simple keyword check
            if topic.lower() in msg.message_text.lower():
                logger.info(f"Ghost loop detected: '{topic}' discussed in recent messages")
                return True

        return False

    def generate_batched_message(
        self,
        user,
        questions: list,
        corpus: str
    ) -> str:
        """
        Batch multiple questions into one natural, conversational message.

        Args:
            user: User object
            questions: List of question strings
            corpus: User's knowledge graph for context

        Returns:
            Natural batched message
        """
        if len(questions) == 1:
            return questions[0]

        # Use Gemini to batch naturally
        batch_prompt = f"""You are Muze, a personal biographer. You need to check in with a user about multiple topics.

**User's Name:** {user.display_name or "there"}

**Questions to Ask:**
{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}

**Context (their knowledge graph):**
{corpus[:800]}

**Your Task:**
Combine these questions into ONE natural, friendly message that:
- Feels like a genuine check-in from a friend
- Doesn't feel like a survey or list
- Transitions smoothly between topics
- Keeps it brief (2-4 sentences max)
- Uses their name if appropriate

**Example Good Output:**
"Hey Sarah! Quick check-in: How did the investor pitch go yesterday? Also curious how the MVP launch is shaping up - still on track for next week?"

**Example Bad Output:**
"Hi. I have 3 questions: 1) How is X? 2) How is Y? 3) How is Z?"

Generate the natural batched message now (just the message, nothing else):"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=batch_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=200,
                )
            )

            message = response.text.strip()
            return message

        except Exception as e:
            logger.error(f"Failed to batch questions: {str(e)}")
            # Fallback: just combine with newlines
            return "\n\n".join(questions)

    def send_whatsapp_message(self, to_number: str, message: str) -> bool:
        """
        Send WhatsApp message via Twilio.

        Args:
            to_number: Recipient phone number (e.g., "whatsapp:+31634829116")
            message: Message text to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            self.twilio.messages.create(
                from_=self.from_number,
                to=to_number,
                body=message
            )

            logger.info(f"✅ Message sent to {to_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message to {to_number}: {str(e)}")
            return False

    def process_dispatch_queue(self):
        """
        Main cron job handler - CREATES PENDING NUDGES for admin approval.
        Does NOT send messages automatically.

        This is called by the /api/cron/process-nudges endpoint.
        """
        logger.info("=== DISPATCH QUEUE PROCESSING STARTED (Creating Pending Nudges) ===")

        # Get all users who completed onboarding
        users = get_users_for_dispatch()
        logger.info(f"Processing {len(users)} users for pending nudges")

        created_count = 0
        skipped_count = 0

        for user in users:
            phone = user.phone_number

            try:
                # 1. Get user data
                open_loops = user.open_loops or {}
                corpus = get_user_corpus(phone) or ""

                if not open_loops:
                    logger.info(f"No open loops for {phone}, skipping")
                    skipped_count += 1
                    continue

                # 2. Generate candidate questions

                candidates = []  # List of (question, weight, topic) tuples

                # Rule A: Check for upcoming events (happening today or tomorrow)
                upcoming = self.state_manager.get_upcoming_events(open_loops, days_ahead=2)
                for topic, event_date, days_until in upcoming:
                    # Skip if pending nudge already exists
                    if check_existing_pending_nudge(phone, topic):
                        continue

                    if days_until == 0:
                        question = f"Big day today - how did {topic} go?"
                        weight = 5
                    elif days_until == 1:
                        question = f"Tomorrow's the day for {topic} - feeling ready?"
                        weight = 5
                    else:
                        loop_data = open_loops.get(topic, {})
                        question = self.state_manager.generate_check_in_question(
                            topic, loop_data, corpus
                        )
                        weight = loop_data.get('weight', 4)

                    candidates.append((question, weight, topic))

                # Rule B: Check for decaying topics (7+ days without update)
                decaying = self.state_manager.detect_decaying_loops(open_loops, days_threshold=7)
                for topic in decaying:
                    # Skip if pending nudge already exists
                    if check_existing_pending_nudge(phone, topic):
                        continue

                    loop_data = open_loops.get(topic, {})
                    question = self.state_manager.generate_check_in_question(
                        topic, loop_data, corpus
                    )
                    weight = loop_data.get('weight', 3)
                    candidates.append((question, weight, topic))

                # Rule C: Check for high-weight loops ready based on pacing
                # This ensures high-priority topics get regular check-ins even without events or decay
                now = datetime.utcnow()
                for topic, loop_data in open_loops.items():
                    # Skip if already a candidate from Rules A or B
                    if any(c[2] == topic for c in candidates):
                        continue

                    # Skip if pending nudge already exists
                    if check_existing_pending_nudge(phone, topic):
                        continue

                    weight = loop_data.get('weight', 3)
                    last_updated = loop_data.get('last_updated')

                    # Only consider weight 4-5 loops for proactive check-ins
                    if weight < 4:
                        continue

                    # Check if enough time has passed based on weight
                    if last_updated:
                        try:
                            from dateutil import parser
                            last_updated_dt = parser.parse(last_updated)
                            hours_since = (now - last_updated_dt).total_seconds() / 3600

                            # Pacing thresholds for proactive check-ins
                            # More conservative than real-time pacing to avoid over-messaging
                            if weight >= 5:
                                threshold = 48  # 2 days for weight 5 (high priority)
                            else:  # weight 4
                                threshold = 96  # 4 days for weight 4 (medium-high priority)

                            if hours_since >= threshold:
                                question = self.state_manager.generate_check_in_question(
                                    topic, loop_data, corpus
                                )
                                candidates.append((question, weight, topic))
                                logger.info(f"Rule C: Added weight {weight} loop '{topic}' (last updated {hours_since:.1f}h ago)")
                        except Exception as e:
                            logger.error(f"Error parsing last_updated for {topic}: {str(e)}")
                            continue

                if not candidates:
                    logger.info(f"No candidates for {phone}, skipping")
                    skipped_count += 1
                    continue

                # 3. Filter candidates

                # Sort by weight (highest first)
                candidates.sort(key=lambda x: x[1], reverse=True)

                # Get highest weight
                max_weight = candidates[0][1]

                # Check pacing for highest weight
                if not self.should_send_based_on_pacing(user, max_weight):
                    logger.info(f"Pacing not met for {phone} (weight {max_weight}), skipping")
                    skipped_count += 1
                    continue

                # Ghost loop check
                valid_candidates = []
                for question, weight, topic in candidates:
                    if not self.check_ghost_loops(user, topic):
                        valid_candidates.append((question, weight, topic))

                if not valid_candidates:
                    logger.info(f"All candidates are ghost loops for {phone}, skipping")
                    skipped_count += 1
                    continue

                # 4. Create pending nudges (up to 3)

                top_candidates = valid_candidates[:3]

                # Calculate scheduled send time
                # Use weight-based pacing from last interaction
                if user.last_interaction_at:
                    last_interaction = user.last_interaction_at
                else:
                    last_interaction = datetime.utcnow()

                # Weight-based pacing
                weight = top_candidates[0][1]
                if weight >= 5:
                    hours_to_add = 4
                elif weight >= 3:
                    hours_to_add = 24
                else:
                    hours_to_add = 48

                scheduled_time = last_interaction + timedelta(hours=hours_to_add)

                # Ensure it's not in quiet hours
                user_tz = pytz.timezone(user.timezone)
                scheduled_time_user_tz = scheduled_time.replace(tzinfo=pytz.utc).astimezone(user_tz)

                # If in quiet hours, move to end of quiet hours
                if self.is_quiet_hours_at_time(user, scheduled_time_user_tz):
                    scheduled_time_user_tz = scheduled_time_user_tz.replace(
                        hour=user.quiet_hours_end,
                        minute=0,
                        second=0
                    )
                    # If that time has passed today, move to tomorrow
                    if scheduled_time_user_tz < datetime.now(user_tz):
                        scheduled_time_user_tz += timedelta(days=1)

                    scheduled_time = scheduled_time_user_tz.astimezone(pytz.utc).replace(tzinfo=None)

                # Create pending nudge for each candidate
                for question, weight, topic in top_candidates:
                    try:
                        nudge = create_pending_nudge(
                            phone_number=phone,
                            topic=topic,
                            weight=weight,
                            message_text=question,
                            scheduled_send_time=scheduled_time
                        )
                        created_count += 1
                        logger.info(f"✅ Created pending nudge for {phone} on topic '{topic}'")
                    except Exception as e:
                        logger.error(f"Failed to create pending nudge for {phone}/{topic}: {str(e)}")
                        continue

            except Exception as e:
                logger.error(f"Error processing {phone}: {str(e)}")
                skipped_count += 1
                continue

        logger.info(f"=== DISPATCH COMPLETE: Created={created_count}, Skipped={skipped_count} ===")
        return {"sent": created_count, "skipped": skipped_count}

    def is_quiet_hours_at_time(self, user, check_time):
        """Check if a specific time is within quiet hours"""
        hour = check_time.hour
        quiet_start = user.quiet_hours_start
        quiet_end = user.quiet_hours_end

        if quiet_start > quiet_end:
            return hour >= quiet_start or hour < quiet_end
        else:
            return quiet_start <= hour < quiet_end


    def send_approved_nudges(self):
        """
        Send all approved nudges that are ready (scheduled_send_time has passed).
        This should be called frequently (e.g., every 5-10 minutes) to send approved messages.
        """
        from database import get_approved_nudges_ready_to_send, update_pending_nudge
        
        logger.info("=== CHECKING FOR APPROVED NUDGES TO SEND ===")
        
        nudges = get_approved_nudges_ready_to_send()
        sent_count = 0
        failed_count = 0
        
        for nudge in nudges:
            try:
                # Send the message
                success = self.send_whatsapp_message(nudge.phone_number, nudge.message_text)
                
                if success:
                    # Store as outgoing message
                    store_message(nudge.phone_number, "outgoing", nudge.message_text)
                    
                    # Update last_interaction_at
                    update_user_interaction(nudge.phone_number)
                    
                    # Mark nudge as sent
                    update_pending_nudge(nudge.id, status="sent", sent_at=datetime.utcnow())
                    
                    sent_count += 1
                    logger.info(f"✅ Sent approved nudge #{nudge.id} to {nudge.phone_number}")
                else:
                    failed_count += 1
                    logger.error(f"❌ Failed to send nudge #{nudge.id}")
                    
            except Exception as e:
                logger.error(f"Error sending nudge #{nudge.id}: {str(e)}")
                failed_count += 1
                continue
        
        logger.info(f"=== APPROVED NUDGES SENT: {sent_count} sent, {failed_count} failed ===")
        return {"sent": sent_count, "failed": failed_count}

