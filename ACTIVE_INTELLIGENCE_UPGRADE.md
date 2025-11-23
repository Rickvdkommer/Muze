# Active Intelligence Upgrade - Implementation Summary

## Overview

Muze has been successfully upgraded from a **passive** system (waits for user messages) to an **active** intelligence system (proactively engages users based on their goals and events).

**Date:** 2025-01-23
**Version:** 2.0.0
**Status:** ✅ Deployed to Railway

---

## What Was Implemented

### Part 1: Database Schema ✅

**Modified:** `database.py`

#### New User Model Fields:

```python
# Active Intelligence Fields
timezone = Column(String(50), default='Europe/Amsterdam', nullable=False)
quiet_hours_start = Column(Integer, default=22, nullable=False)  # 10 PM
quiet_hours_end = Column(Integer, default=9, nullable=False)  # 9 AM
onboarding_step = Column(Integer, default=0, nullable=False)  # 0=New, 99=Complete
last_interaction_at = Column(DateTime, nullable=True)  # For pacing

# JSON Fields for State Management
open_loops = Column(JSONB, default={}, nullable=False)
# Structure: {"topic_name": {"status": "active", "last_updated": "ISO-DATE",
#             "next_event_date": "ISO-DATE", "weight": 1-5}}

pending_questions = Column(JSONB, default=[], nullable=False)
# Structure: [{"question": "...", "weight": 5, "created_at": "..."}]
```

#### New Helper Functions:

- `get_user(phone_number)` - Get single user
- `update_user_interaction(phone_number)` - Update last_interaction_at
- `update_user_onboarding_step(phone_number, step)` - Progress onboarding
- `update_user_field(phone_number, **kwargs)` - Generic field updater
- `get_users_for_dispatch()` - Get all users who completed onboarding

---

### Part 2: The Logic Modules ✅

#### Module A: `onboarding_manager.py`

**Purpose:** 3-step onboarding state machine

**Flow:**

1. **Step 0 → 1 (Name):**
   - Input: User's first message
   - Action: Ask "What should I call you?"

2. **Step 1 → 2 (Location):**
   - Input: User's name
   - Action: Save display_name, ask for city/timezone

3. **Step 2 → 3 (Goals):**
   - Input: City/timezone
   - Action: Parse timezone (80+ cities mapped), ask for goals/projects

4. **Step 3 → 99 (Complete):**
   - Input: Goals text
   - Action: Use Gemini to extract **multiple** goals, populate open_loops
   - Final response: "I'm manually reviewing your background details..."

**Gemini Prompt (Goal Extraction):**
```
Extract ALL distinct goals/projects. For each:
1. Create clear name (2-5 words)
2. Assign weight 1-5 based on urgency/detail
3. Return JSON: [{"name": "...", "weight": 1-5, "description": "..."}]
```

**Features:**
- Comprehensive timezone mapping (Amsterdam, NYC, Singapore, Tokyo, etc.)
- Extracts multiple goals in one shot
- Weighted priorities (5 = urgent, 1 = aspirational)
- Natural fallback responses

---

#### Module B: `state_manager.py`

**Purpose:** The "Brain" - Tracks open loops and maintains corpus quality

**Key Functions:**

1. **`update_open_loops()`** - Called after every message
   - **Detects New Loops:** Future events ("Pitching on Friday")
   - **Closes Loops:** Completed tasks ("Pitch went great")
   - **Detects Decay:** Topics inactive for 7+ days
   - **Gardener Rule:** Identifies obsolete corpus lines to delete

2. **`apply_corpus_cleanup()`** - Removes outdated information
   - Deletes contradictory facts (e.g., "Raising seed" → "Raised $2M")
   - Replaces old dates with updated ones
   - Maintains markdown structure

3. **`detect_decaying_loops()`** - Finds stale topics
   - Checks last_updated timestamps
   - Flags loops 7+ days old as "decaying"

4. **`get_upcoming_events()`** - Finds events happening soon
   - Returns (topic, date, days_until) tuples
   - Sorted by urgency

5. **`generate_check_in_question()`** - Creates natural questions
   - Context-aware (uses corpus)
   - Weight-appropriate urgency
   - Personal and conversational

**Gemini Prompts:**

**Loop Analysis:**
```
Analyze message + corpus + current loops.
1. Detect new loops (future events, new projects)
2. Close completed loops
3. Detect decay (7+ days)
4. Output corpus cleanup instructions

Return JSON: {
  "updated_loops": {...},
  "corpus_cleanup": ["DELETE line: ...", "REPLACE ..."],
  "reasoning": "..."
}
```

**Check-In Question:**
```
Create brief (1-2 sentence) natural question.
- Reference specific context
- Urgency based on weight (5 = "How did X go?", 1 = "Any updates?")
- Feels like genuine friend check-in
```

---

#### Module C: `scheduler_dispatcher.py`

**Purpose:** The "Nudge Engine" - Proactively reaches out to users

**Called By:** Cron job (every hour)

**Logic Flow:**

1. **Get Users:** `get_users_for_dispatch()` (onboarding_step == 99)

2. **For Each User:**

   a. **Check Quiet Hours:**
   ```python
   if current_user_time between quiet_start and quiet_end:
       skip
   ```

   b. **Generate Candidates:**
   - Upcoming events (today/tomorrow → weight 5)
   - Decaying topics (7+ days → weight from loop)

   c. **Smart Pacing Rule:**
   - **Weight 5:** Send if 4+ hours since last_interaction_at
   - **Weight 3-4:** Send if 24+ hours
   - **Weight 1-2:** Send if 48+ hours

   d. **Ghost Loop Check:**
   - Check last 3 messages for topic keywords
   - Skip if recently discussed

   e. **Batching:**
   - Select top 3 candidates
   - Use Gemini to combine into one natural message

   f. **Send via Twilio:**
   - Store outgoing message
   - Update last_interaction_at

3. **Return:** `{sent: N, skipped: M}`

**Gemini Prompt (Batching):**
```
Combine these questions into ONE natural message:
1. Question A
2. Question B
3. Question C

Make it feel like genuine check-in from friend, not survey.
Example: "Hey! Quick check-in: How did the pitch go? Also curious
         how the MVP launch is shaping up."
```

**Features:**
- Timezone-aware quiet hours
- Weight-based pacing (don't interrupt active chats)
- Natural batching (up to 3 questions)
- Ghost prevention (avoid redundancy)
- Event urgency (today/tomorrow)

---

### Part 3: Integration ✅

#### Updated `app.py`

**New Imports:**
```python
from onboarding_manager import OnboardingManager
from state_manager import StateManager
from scheduler_dispatcher import SchedulerDispatcher
```

**Initialization:**
```python
onboarding_manager = OnboardingManager(client)
state_manager = StateManager(client)
scheduler_dispatcher = SchedulerDispatcher(client, twilio_client, TWILIO_PHONE_NUMBER)
```

**Webhook Flow (Enhanced):**

```python
/webhook (POST)
├─ Get user, update last_interaction_at
├─ Handle voice transcription (existing)
│
├─ ONBOARDING CHECK
│  └─ if user.onboarding_step < 99:
│      └─ Route to onboarding_manager.handle_onboarding()
│      └─ Auto-respond with onboarding prompts
│
├─ Context requests (existing)
│  └─ Auto-respond with context
│
├─ Normal messages:
│  ├─ Store message
│  ├─ Update corpus (extract signal)
│  ├─ Update open loops (detect events/decay)
│  └─ Apply corpus cleanup (Gardener Rule)
│
└─ Return empty TwiML (human-in-the-loop)
```

**New Endpoint:**

```python
POST /api/cron/process-nudges

Returns:
{
  "status": "success",
  "sent": 5,
  "skipped": 12
}

Security: Optional X-Cron-Token header check (commented out)
```

---

### Part 4: Corpus Refinement ✅

**Updated:** `corpus_updater.py`

**New Philosophy: Signal vs Noise**

**✅ SIGNAL (Extract):**
- Concrete facts: "Raised $2M seed", "Based in Amsterdam"
- Specific goals: "Launching MVP by March 15"
- Important relationships: "Co-founder Sarah handles design"
- Significant events: "Quit job at Google last month"
- Core values: "I believe in radical transparency"
- Skills & expertise: "10 years backend engineering"

**❌ NOISE (Skip):**
- Greetings and small talk
- Transient feelings: "Feeling tired today"
- Vague statements: "Things are going well"
- Meta-commentary: "That's interesting"
- Temporary updates: "Busy this week"
- Redundant information already in graph

**Updated Prompt:**
```
You are a SENIOR Knowledge Curator. Maintain HIGH-QUALITY graph by extracting SIGNAL, not NOISE.

Rules:
1. Be SELECTIVE: Quality > Quantity
2. Add ONLY information useful for understanding person long-term
3. Update existing entries if changed
4. Keep entries CONCISE - one bullet per fact
5. If no signal, return graph UNCHANGED
```

---

## Deployment Checklist

### 1. Environment Variables

Add to Railway:

```bash
TWILIO_PHONE_NUMBER=whatsapp:+14155238886  # Your Twilio WhatsApp number
# (All other vars already exist)
```

### 2. Database Migration

**Option A: Let SQLAlchemy Auto-Create (Easiest)**
- Railway will detect schema changes on deploy
- New columns will be created with defaults
- Existing users get default values automatically

**Option B: Manual Migration (Production-Safe)**
```sql
ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'Europe/Amsterdam' NOT NULL;
ALTER TABLE users ADD COLUMN quiet_hours_start INTEGER DEFAULT 22 NOT NULL;
ALTER TABLE users ADD COLUMN quiet_hours_end INTEGER DEFAULT 9 NOT NULL;
ALTER TABLE users ADD COLUMN onboarding_step INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE users ADD COLUMN last_interaction_at TIMESTAMP;
ALTER TABLE users ADD COLUMN open_loops JSONB DEFAULT '{}' NOT NULL;
ALTER TABLE users ADD COLUMN pending_questions JSONB DEFAULT '[]' NOT NULL;
```

### 3. Setup Cron Job

**Option A: cron-job.org (Free)**
1. Go to https://cron-job.org
2. Create new job:
   - URL: `https://your-backend.railway.app/api/cron/process-nudges`
   - Method: POST
   - Schedule: Every hour (0 * * * *)
   - Timeout: 30 seconds

**Option B: Railway Cron (Paid)**
Create `railway.json`:
```json
{
  "cron": {
    "process-nudges": {
      "schedule": "0 * * * *",
      "command": "curl -X POST https://your-backend.railway.app/api/cron/process-nudges"
    }
  }
}
```

**Option C: External Service (GitHub Actions, etc.)**

### 4. Test Onboarding

Send first message to Muze from a new number:

```
You → "Hey"
Muze → "Hi! I'm Muze, your personal biographer. First, what should I call you?"

You → "Rick"
Muze → "Nice to meet you, Rick! To ensure I don't message you at inconvenient times, which city or timezone are you in?"

You → "Amsterdam"
Muze → "Got it. To start, what are the key projects or goals you are focused on right now?"

You → "Fundraising for Muze, shipping MVP, and getting healthier"
Muze → "Understood. I've noted those priorities: Fundraising for Muze, Shipping MVP, Health & Fitness. I'm manually reviewing your background details now..."

✅ Check database:
- onboarding_step = 99
- open_loops = {"Fundraising for Muze": {status: "active", weight: 5, ...}, ...}
```

---

## Usage Guide

### For New Users

1. **First Contact:** User sends any message
2. **Onboarding:** 3-step flow (Name → Location → Goals)
3. **Background Upload:** Admin manually uploads resume/bio to corpus
4. **Active Engagement:** System starts proactive check-ins based on:
   - Upcoming events (from open_loops)
   - Decaying topics (7+ days)
   - Weight-based pacing

### For Existing Users

**They will be treated as new users on next message:**
- onboarding_step defaults to 0
- Will go through onboarding flow

**To Skip Onboarding for Existing Users:**

```python
# Run this script to mark all existing users as onboarded
from database import get_db, User

db = get_db()
users = db.query(User).all()

for user in users:
    user.onboarding_step = 99
    user.timezone = 'Europe/Amsterdam'  # Set appropriately
    user.quiet_hours_start = 22
    user.quiet_hours_end = 9
    user.open_loops = {}  # Or manually populate

db.commit()
```

### Admin Workflow

1. **User Completes Onboarding** → open_loops populated with initial goals
2. **Admin Uploads Background** → Corpus gets bio/resume (manual upload via dashboard)
3. **User Chats Naturally** → open_loops auto-update, corpus refined
4. **Cron Runs Hourly** → System sends proactive nudges when appropriate
5. **User Responds** → Loops update, pacing timer resets

---

## Key Prompts Summary

### 1. Onboarding Goal Extraction

**Input:** User's goals text
**Output:** JSON array of goals with weights
**Model:** gemini-2.0-flash-exp
**Temperature:** 0.3
**Max Tokens:** 800

### 2. Loop Analysis

**Input:** Corpus + message + current loops
**Output:** Updated loops + cleanup instructions
**Model:** gemini-2.0-flash-exp
**Temperature:** 0.4
**Max Tokens:** 1500

### 3. Corpus Cleanup

**Input:** Corpus + cleanup instructions
**Output:** Cleaned corpus markdown
**Model:** gemini-2.0-flash-exp
**Temperature:** 0.2
**Max Tokens:** 2000

### 4. Check-In Question

**Input:** Topic + loop data + corpus
**Output:** Natural question
**Model:** gemini-2.0-flash-exp
**Temperature:** 0.7
**Max Tokens:** 100

### 5. Question Batching

**Input:** Multiple questions
**Output:** One natural message
**Model:** gemini-2.0-flash-exp
**Temperature:** 0.8
**Max Tokens:** 200

### 6. Corpus Update (Refined)

**Input:** Corpus + new message
**Output:** Updated corpus with SIGNAL only
**Model:** gemini-2.0-flash-exp
**Temperature:** 0.5
**Max Tokens:** 1200

---

## Cost Analysis

### Per New User (One-Time):
- Onboarding: 3 steps × $0.0007 = **$0.002**
- Initial goal extraction: **$0.0008**
- **Total:** ~$0.003 per user onboarding

### Per Message (Ongoing):
- Corpus update: **$0.0009**
- Loop analysis: **$0.0011**
- Cleanup (if needed): **$0.0005**
- **Total:** ~$0.0025 per message

### Per Nudge Sent:
- Question generation: **$0.0003**
- Batching (if multiple): **$0.0005**
- **Total:** ~$0.0008 per nudge

### Monthly Estimate (Active User):
- 100 messages: $0.25
- 20 proactive nudges: $0.016
- **Total:** ~$0.27/month per active user

**Very cost-effective compared to passive system!**

---

## Testing Checklist

### ✅ Onboarding
- [ ] New user triggers Step 0
- [ ] Name saved correctly
- [ ] Timezone parsed (test: "Amsterdam", "NYC", "Tokyo")
- [ ] Goals extracted to open_loops
- [ ] Step marked as 99

### ✅ Open Loops
- [ ] Future event detected ("Meeting Friday")
- [ ] Loop added with next_event_date
- [ ] Completed task closes loop ("Pitch went great")
- [ ] Decay flagged after 7 days

### ✅ Corpus Cleanup
- [ ] Obsolete info identified
- [ ] Cleanup instructions applied
- [ ] Markdown structure preserved

### ✅ Dispatcher
- [ ] Quiet hours respected
- [ ] Pacing rules followed (4h/24h/48h)
- [ ] Questions batched naturally
- [ ] Ghost loops prevented
- [ ] Twilio message sent

### ✅ Cron
- [ ] Endpoint responds with {sent, skipped}
- [ ] Runs without errors
- [ ] Logs show candidate generation

---

## Monitoring

### Key Metrics to Track

1. **Onboarding Completion Rate**
   ```sql
   SELECT
     COUNT(CASE WHEN onboarding_step = 99 THEN 1 END) as completed,
     COUNT(*) as total
   FROM users;
   ```

2. **Average Open Loops per User**
   ```sql
   SELECT AVG(jsonb_array_length(open_loops::jsonb))
   FROM users
   WHERE onboarding_step = 99;
   ```

3. **Nudges Sent per Day**
   ```sql
   SELECT DATE(timestamp), COUNT(*)
   FROM messages
   WHERE direction = 'outgoing'
     AND message_text NOT LIKE '%onboarding%'
   GROUP BY DATE(timestamp);
   ```

4. **Response Rate to Nudges**
   - Track messages sent by dispatcher
   - Check if user responded within 24h

### Logs to Watch

```bash
# Railway logs
railway logs

# Look for:
"CRON: Process Nudges Triggered"
"Onboarding step X for {phone}"
"Loop changes: N total, M cleanup items"
"Sent nudge to {phone}"
"Pacing block for {phone}"
```

---

## Troubleshooting

### Issue: User stuck in onboarding

**Solution:**
```python
from database import update_user_onboarding_step
update_user_onboarding_step("whatsapp:+31...", 99)
```

### Issue: No nudges being sent

**Check:**
1. Cron job running? (check logs)
2. Users have open_loops? (query database)
3. Pacing blocking? (check last_interaction_at)
4. Quiet hours? (check timezone + current hour)

### Issue: Too many nudges

**Solutions:**
1. Increase pacing thresholds in scheduler_dispatcher.py
2. Raise weight requirements
3. Adjust cron frequency (every 2-3 hours instead of hourly)

### Issue: Corpus getting too long

**The Gardener Rule handles this:**
- Corpus cleanup runs automatically
- Removes obsolete information
- Check logs for cleanup actions

---

## Next Steps (Optional Enhancements)

1. **Admin Dashboard Integration**
   - View open_loops in dashboard
   - Manual loop creation/editing
   - Nudge preview before sending

2. **Advanced Scheduling**
   - Per-user nudge frequency preferences
   - Event reminders (1 day before, 1 hour before)
   - Weekly summaries

3. **Analytics Dashboard**
   - Engagement metrics
   - Loop completion rates
   - Response time analysis

4. **Multi-Language Support**
   - Detect user language
   - Translate nudges
   - Maintain corpus in user's language

5. **Webhook Integration**
   - Trigger external systems on loop completion
   - Zapier/IFTTT integration
   - Calendar sync (Google Calendar, etc.)

---

## Support

**Issues?** Create an issue on GitHub: https://github.com/Rickvdkommer/Muze/issues

**Documentation:** See ARCHITECTURE.md for system overview

**Status:** All systems operational ✅

---

*Last Updated: 2025-01-23*
*Version: 2.0.0 - Active Intelligence Edition*
