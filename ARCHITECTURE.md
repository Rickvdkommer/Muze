# Muze - Personal Biographer Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [What Muze Does](#what-muze-does)
3. [System Architecture](#system-architecture)
4. [Component Breakdown](#component-breakdown)
5. [Data Flow](#data-flow)
6. [User Guide](#user-guide)
7. [Admin Guide](#admin-guide)
8. [API Reference](#api-reference)
9. [Cost Analysis](#cost-analysis)
10. [Deployment](#deployment)

---

## Overview

**Muze** is a WhatsApp-based personal biographer that:
- Learns about users through conversations
- Maintains a personal knowledge graph for each user
- Provides context extraction for AI prompt engineering
- Supports text and voice messages
- Uses human-in-the-loop for quality control

### Tech Stack
- **Backend**: Python 3.12, Flask, Gunicorn
- **Database**: PostgreSQL (Railway addon)
- **AI**: Google Gemini 2.0 Flash
- **Messaging**: Twilio WhatsApp API
- **Dashboard**: Next.js 14, TypeScript, React
- **Hosting**:
  - Backend: Railway.app
  - Frontend: Vercel
  - Domain: www.heymuze.app

---

## What Muze Does

### For End Users (via WhatsApp)

#### 1. **Conversational Learning**
Users chat with Muze about their life, work, goals, and experiences. Muze:
- Asks thoughtful follow-up questions
- Shows genuine interest and empathy
- Keeps responses brief (1-2 sentences, <200 chars when possible)
- Remembers everything from previous conversations

#### 2. **Personal Knowledge Graph**
Every meaningful conversation updates the user's corpus (knowledge graph):
- **Worldview**: Philosophies, perspectives, beliefs
- **Personal History**: Background, experiences, milestones
- **Values & Beliefs**: Core principles and ethics
- **Goals & Aspirations**: Dreams, plans, ambitions
- **Relationships**: Important people and connections
- **Interests & Hobbies**: Passions and pastimes
- **Projects & Work**: Current work, startups, projects

#### 3. **Context Retrieval**
Users can request context about any topic:
```
User: "provide context on Muze"
Muze: [Returns detailed markdown about the Muze project from your corpus]
```

This context can be copied and pasted into ChatGPT, Claude, or any other AI to give them instant understanding of your topic.

#### 4. **Voice Message Support**
Users can send voice messages instead of typing:
- Automatically transcribed using Gemini 2.0 Flash
- Processed as normal text
- Very cheap: ~$0.00135 per minute
- Supports all WhatsApp audio formats

### For Admins (via Dashboard)

#### 1. **Message Queue Management**
- View all unprocessed messages
- See AI-suggested responses
- Edit responses before sending
- Character counter (1600 char WhatsApp limit)
- Skip messages if not relevant

#### 2. **User Corpus Management**
- View all users who have messaged Muze
- Read/edit each user's knowledge graph
- See message count and last activity
- Direct corpus editing for corrections

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          End User                                │
│                     (WhatsApp Interface)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Text/Voice Messages
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Twilio WhatsApp API                         │
│                  (Message Gateway & Media)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ POST /webhook
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Backend (Railway)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  app.py (Main Application)                               │   │
│  │  - Webhook endpoint                                      │   │
│  │  - REST API endpoints                                    │   │
│  │  - CORS configuration                                    │   │
│  └────────┬────────────┬────────────┬────────────┬──────────┘   │
│           │            │            │            │              │
│  ┌────────▼──────┐ ┌──▼──────┐ ┌──▼──────┐ ┌──▼───────────┐   │
│  │ Audio         │ │ Context │ │ Corpus  │ │ Database     │   │
│  │ Transcriber   │ │Extractor│ │ Updater │ │ Interface    │   │
│  │               │ │         │ │         │ │              │   │
│  │ - Download    │ │ - Pattern│ │ - Smart │ │ - User CRUD  │   │
│  │   from Twilio │ │   match │ │   filter│ │ - Message    │   │
│  │ - Transcribe  │ │ - Extract│ │ - AI    │ │   storage    │   │
│  │   via Gemini  │ │   topics│ │   extract│ │ - Corpus mgmt│   │
│  └───────────────┘ └─────────┘ └─────────┘ └──────┬───────┘   │
│                                                     │           │
└─────────────────────────────────────────────────────┼───────────┘
                                                      │
                            ┌─────────────────────────▼───────────┐
                            │   PostgreSQL Database (Railway)     │
                            │   - users table                     │
                            │   - messages table                  │
                            │   - user_corpus table               │
                            └─────────────────────────────────────┘
                                                      ▲
                                                      │
┌─────────────────────────────────────────────────────┼───────────┐
│              Next.js Dashboard (Vercel)             │           │
│              www.heymuze.app                        │           │
│                                                     │           │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────▼────────┐  │
│  │ Login Page   │  │ Message Queue  │  │ User Corpus       │  │
│  │              │  │                │  │ Viewer            │  │
│  │ - Password   │  │ - Unprocessed  │  │                   │  │
│  │   auth       │  │   messages     │  │ - User list       │  │
│  │              │  │ - AI response  │  │ - Corpus display  │  │
│  │              │  │ - Edit & send  │  │ - Inline editing  │  │
│  └──────────────┘  └────────────────┘  └───────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### Backend Components

#### 1. **app.py** (Main Flask Application)
**Purpose**: Central application server handling all requests

**Key Functions**:
- `webhook()`: Receives WhatsApp messages from Twilio
  - Detects voice messages and transcribes them
  - Checks for context requests (auto-responds)
  - Updates corpus automatically on message receipt
  - Stores messages for human review
- API endpoints for dashboard integration

**Environment Variables**:
```bash
GEMINI_API_KEY=<your-gemini-key>
TWILIO_ACCOUNT_SID=<your-twilio-sid>
TWILIO_AUTH_TOKEN=<your-twilio-token>
DATABASE_URL=<postgres-connection-string>
```

#### 2. **audio_transcriber.py**
**Purpose**: Handle voice message transcription

**Key Methods**:
- `download_audio()`: Downloads audio from Twilio MediaUrl with auth
- `transcribe_audio()`: Sends audio to Gemini for transcription
- `process_voice_message()`: Complete pipeline (download + transcribe)

**Cost**: ~$0.00135 per minute (4.4x cheaper than OpenAI Whisper)

**Supported Formats**: audio/ogg, audio/mpeg, audio/mp4, audio/amr, audio/aac

#### 3. **context_extractor.py**
**Purpose**: Extract relevant context for AI prompting

**Key Methods**:
- `is_context_request()`: Detects context request patterns
- `extract_topic()`: Parses topic from message
- `generate_context()`: Creates markdown-formatted context from corpus
- `handle_context_request()`: Main handler (returns bool, response)

**Patterns Detected**:
- "provide context on X"
- "give me context about X"
- "what do you know about X"
- "tell me about X"

**Output**: Clean markdown (<1600 chars) ready to copy-paste into other LLMs

#### 4. **corpus_updater.py**
**Purpose**: Automatically update user knowledge graphs

**Key Methods**:
- `should_update_corpus()`: Smart filtering (skips greetings, small talk)
- `update_corpus()`: Extracts insights and updates knowledge graph
- `batch_update_from_recent_messages()`: Catch up on missed updates

**Intelligence**:
- Skips messages <10 chars
- Skips common greetings ("hi", "hello", "ok")
- Detects personal markers ("I am", "my", "I work", etc.)
- Uses Gemini to extract meaningful information
- Only updates if significant content found

**Configuration**:
- Temperature: 0.5 (balanced extraction)
- Max tokens: 1200 (detailed updates)
- Model: gemini-2.0-flash-exp

#### 5. **database.py**
**Purpose**: Database models and utilities

**Models**:
```python
User:
  - phone_number (PRIMARY KEY)
  - display_name
  - created_at
  - last_message_at

Message:
  - id
  - phone_number (FK to User)
  - direction ('incoming' | 'outgoing')
  - message_text
  - timestamp
  - processed (boolean)

UserCorpus:
  - phone_number (FK to User)
  - corpus_text (markdown)
  - updated_at
```

**Key Functions**:
- `get_or_create_user()`: Auto-create user on first message
- `store_message()`: Store incoming/outgoing messages
- `get_user_corpus()`: Retrieve knowledge graph
- `update_user_corpus()`: Update knowledge graph
- `get_unprocessed_messages()`: Queue for dashboard
- `mark_message_processed()`: Mark as handled

### Frontend Components (Next.js Dashboard)

#### 1. **LoginPage.tsx**
- Simple password authentication
- Stores auth in localStorage
- Redirects to message queue on success

#### 2. **MessageQueue.tsx**
- Displays unprocessed messages in chronological order
- Shows phone number, timestamp, message preview
- Click to view full message details
- Auto-refreshes every 10 seconds

#### 3. **MessageDetail.tsx**
- Shows full incoming message
- Generates AI response automatically
- Editable response textarea
- Character counter (1600 limit with warning)
- View user's corpus (collapsible)
- Send or Skip buttons
- Sends via secure server-side Twilio API

#### 4. **UserCorpusViewer.tsx**
- Lists all users with last message time
- Click user to view their corpus
- Markdown rendering with ReactMarkdown
- Inline editing capability
- Save/Discard changes

#### 5. **API Integration (lib/api.ts)**
```typescript
// Backend API calls
getAllUsers()
getUserMessages(phoneNumber, limit)
getUserCorpus(phoneNumber)
updateUserCorpus(phoneNumber, corpus)
getUnprocessedMessages(limit)
markMessageProcessed(messageId)
generateAIResponse(phoneNumber, message)
sendWhatsAppMessage(to, message) // Secure server-side
```

#### 6. **Server-Side Twilio Endpoint (app/api/send-message/route.ts)**
- Handles Twilio API calls server-side
- Credentials never exposed to browser
- POST /api/send-message with {to, message}
- Returns success/error

---

## Data Flow

### Flow 1: Normal Text Message

```
1. User sends WhatsApp message
   └─> Twilio receives message
       └─> POST to /webhook with Body="Hello Muze"

2. Backend webhook():
   └─> Checks NumMedia (0 in this case)
   └─> Checks if context request (no)
   └─> Stores message in database
   └─> Calls corpus_updater.update_corpus()
       └─> Gemini extracts insights
       └─> Updates user's knowledge graph
   └─> Returns empty TwiML (no auto-reply)

3. Dashboard polls /api/messages/unprocessed
   └─> Sees new message
   └─> Displays in queue

4. Admin clicks message:
   └─> Calls /api/generate-response
       └─> Retrieves user corpus
       └─> Gemini generates personalized response
   └─> Admin edits if needed
   └─> Clicks "Send Response"
       └─> POST to /api/send-message (server-side)
           └─> Twilio sends WhatsApp message
       └─> POST to /api/messages/{id}/process
           └─> Marks message as processed
       └─> Removed from queue
```

### Flow 2: Voice Message

```
1. User sends voice message
   └─> Twilio receives audio
       └─> POST to /webhook with:
           NumMedia=1
           MediaUrl0=https://api.twilio.com/.../media/...
           MediaContentType0=audio/ogg

2. Backend webhook():
   └─> Detects NumMedia > 0
   └─> Checks MediaContentType0.startswith('audio/')
   └─> Calls audio_transcriber.process_voice_message()
       └─> Downloads audio from MediaUrl with auth
       └─> Sends to Gemini with audio bytes
       └─> Receives transcription
   └─> Sets incoming_msg = "[Voice message]: {transcription}"
   └─> Continues normal flow (corpus update, storage)

3. Rest of flow identical to text message
```

### Flow 3: Context Request (Auto-Response)

```
1. User sends "provide context on Muze"
   └─> Twilio receives message
       └─> POST to /webhook

2. Backend webhook():
   └─> Calls context_extractor.handle_context_request()
       └─> Detects context pattern match
       └─> Extracts topic: "Muze"
       └─> Calls generate_context()
           └─> Retrieves user corpus
           └─> Gemini searches corpus for "Muze"
           └─> Generates markdown context (<1600 chars)
       └─> Returns (True, context_markdown)
   └─> Stores incoming message
   └─> Stores outgoing context message
   └─> Marks as processed
   └─> Returns TwiML with context message
       └─> Twilio sends WhatsApp message IMMEDIATELY

3. User receives context instantly
   └─> Can copy-paste into ChatGPT/Claude
```

---

## User Guide

### How to Use Muze (WhatsApp)

#### Starting a Conversation
1. Send a WhatsApp message to the Muze number
2. Introduce yourself, share what you're working on
3. Muze will respond with thoughtful questions

#### Building Your Knowledge Graph
Share information about:
- Your background and expertise
- Current projects and goals
- Values and beliefs
- Relationships and interests
- Work and aspirations

Muze automatically extracts and organizes this into your personal knowledge graph.

#### Getting Context for AI Prompts
When you want to give context to another AI:

```
You: "provide context on my business"

Muze: # Context: My Business

## Overview
Rick is building Muze, a personal branding content creation service...

## Key Information
- Service creates "personal Wikipedia pages"
- Weekly AI conversations build knowledge base
- Solves invisibility to AI-driven search
...
```

Copy this entire message and paste it into your ChatGPT/Claude conversation!

#### Sending Voice Messages
1. Record a voice message in WhatsApp
2. Send it to Muze
3. It will be automatically transcribed and processed as text
4. Your corpus will be updated with the content

---

## Admin Guide

### Accessing the Dashboard
1. Go to www.heymuze.app
2. Enter admin password
3. You'll see the message queue

### Processing Messages

#### Message Queue Tab
- Shows all unprocessed messages
- Click any message to view details
- Auto-refreshes every 10 seconds

#### Message Detail View
1. **Incoming Message**: What the user sent
2. **AI Suggested Response**: Auto-generated by Gemini
3. **Edit Response**: Modify before sending
4. **User Corpus**: Toggle to view their knowledge graph
5. **Send Response**: Sends via WhatsApp and marks processed
6. **Skip**: Marks processed without responding

**Important**: Character counter shows X/1600. WhatsApp limit is 1600 characters. Button disabled if over limit.

### Managing User Corpora

#### Users & Corpus Tab
- Lists all users (sorted by last message)
- Shows phone number, name, last activity
- Click user to view their knowledge graph

#### Viewing/Editing Corpus
1. Select user from list
2. View formatted markdown corpus
3. Click "Edit Corpus" to modify
4. Make changes in textarea
5. Click "Save Changes" or "Discard"

**Use Cases for Editing**:
- Fix incorrect information
- Remove outdated info
- Reorganize sections
- Add manual notes

---

## API Reference

### Public Endpoints

#### POST /webhook
Twilio webhook for incoming WhatsApp messages

**Request** (from Twilio):
```
Body: "message text"
From: "whatsapp:+31634829116"
NumMedia: "0"
MediaUrl0: (if NumMedia > 0)
MediaContentType0: (if NumMedia > 0)
```

**Response**: TwiML (XML)

### Admin API Endpoints

#### GET /api/users
List all users

**Response**:
```json
{
  "count": 5,
  "users": [
    {
      "phone_number": "whatsapp:+31634829116",
      "display_name": "Rick",
      "created_at": "2025-01-15T10:00:00",
      "last_message_at": "2025-01-23T18:40:00"
    }
  ]
}
```

#### GET /api/users/{phone_number}/messages
Get message history

**Query Params**: `?limit=50`

**Response**:
```json
{
  "phone_number": "whatsapp:+31634829116",
  "message_count": 15,
  "messages": [
    {
      "id": 7,
      "direction": "incoming",
      "text": "I'm building Muze...",
      "timestamp": "2025-01-23T18:40:00",
      "processed": false
    }
  ]
}
```

#### GET /api/users/{phone_number}/corpus
Get user's knowledge graph

**Response**:
```json
{
  "phone_number": "whatsapp:+31634829116",
  "corpus": "# Rick's Knowledge Graph\n\n## Worldview\n..."
}
```

#### PUT /api/users/{phone_number}/corpus
Update user's corpus

**Request**:
```json
{
  "corpus": "# Updated knowledge graph..."
}
```

#### GET /api/messages/unprocessed
Get unprocessed message queue

**Query Params**: `?limit=10`

#### POST /api/messages/{id}/process
Mark message as processed

#### POST /api/generate-response
Generate AI response for a message

**Request**:
```json
{
  "phone_number": "whatsapp:+31634829116",
  "message": "Hello, how are you?"
}
```

**Response**:
```json
{
  "response": "I'm doing well, thanks for asking! What have you been working on lately?",
  "phone_number": "whatsapp:+31634829116"
}
```

**Note**: Automatically detects context requests and returns context instead of normal response.

#### POST /api/update-corpus
Update corpus after conversation (usually automatic)

**Request**:
```json
{
  "phone_number": "whatsapp:+31634829116",
  "user_message": "I launched my startup",
  "bot_response": "That's exciting! What does your startup do?"
}
```

---

## Cost Analysis

### Per-Message Costs

#### Text Messages
- **Twilio**: $0.005 per message (WhatsApp)
- **Gemini Response Generation**:
  - Input: ~500 tokens × $0.35/million = $0.000175
  - Output: ~40 tokens × $1.50/million = $0.00006
- **Gemini Corpus Update**:
  - Input: ~800 tokens × $0.35/million = $0.00028
  - Output: ~400 tokens × $1.50/million = $0.0006
- **Total per message**: ~$0.00612

#### Voice Messages (1 minute)
- **Twilio**: $0.005 per message
- **Gemini Transcription**:
  - Audio input: 1,500 tokens × $0.70/million = $0.00105
  - Text output: ~200 tokens × $1.50/million = $0.0003
- **Gemini Response + Corpus**: Same as text (~$0.001)
- **Total per minute of voice**: ~$0.00735

### Monthly Cost Estimates

**Low Usage** (100 messages/month):
- 80 text, 20 voice (1 min avg)
- Cost: ~$0.64/month

**Medium Usage** (500 messages/month):
- 400 text, 100 voice
- Cost: ~$3.18/month

**High Usage** (2000 messages/month):
- 1600 text, 400 voice
- Cost: ~$12.73/month

**Twilio WhatsApp costs not included** (separately billed by Twilio)

### Cost Comparison: Gemini vs Whisper

**Voice transcription (1 minute)**:
- OpenAI Whisper: $0.006/min
- OpenAI Whisper Mini: $0.003/min
- Google Gemini 2.0 Flash: $0.00135/min ✅

**Gemini is 4.4x cheaper than Whisper standard**

---

## Deployment

### Backend (Railway)

**Repository**: https://github.com/Rickvdkommer/Muze

**Configuration**:
1. Connected to GitHub repo
2. Auto-deploys on push to main
3. Detects Python via runtime.txt
4. Uses Procfile for startup: `web: gunicorn app:app`

**Environment Variables** (set in Railway):
```
GEMINI_API_KEY=<your-key>
TWILIO_ACCOUNT_SID=<your-sid>
TWILIO_AUTH_TOKEN=<your-token>
DATABASE_URL=<auto-set-by-railway-postgres>
PORT=<auto-set-by-railway>
```

**Database**: PostgreSQL addon (auto-provisioned)

**Domain**: Custom domain configured in Railway settings

### Frontend (Vercel)

**Repository**: Same repo, /dashboard subdirectory

**Configuration**:
1. Root directory: `dashboard`
2. Framework: Next.js
3. Auto-deploys on push to main

**Environment Variables** (set in Vercel):
```
NEXT_PUBLIC_API_URL=https://your-railway-backend.railway.app
NEXT_PUBLIC_DASHBOARD_PASSWORD=<your-admin-password>
TWILIO_ACCOUNT_SID=<your-sid>
TWILIO_AUTH_TOKEN=<your-token>
TWILIO_PHONE_NUMBER=<your-whatsapp-number>
```

**Domain**: www.heymuze.app (configured in Vercel)

### Twilio Configuration

**WhatsApp Sandbox** (for testing):
1. Go to Twilio Console > Messaging > Try it out > WhatsApp
2. Set webhook URL: `https://your-backend.railway.app/webhook`
3. Method: POST

**Production WhatsApp** (requires approval):
1. Apply for WhatsApp Business API
2. Configure webhook in WhatsApp Senders settings
3. Set URL to your Railway backend /webhook endpoint

---

## Security Considerations

### Credentials
- ✅ Twilio credentials stored server-side only
- ✅ Never exposed to browser (removed NEXT_PUBLIC_ prefix)
- ✅ Dashboard uses secure /api/send-message endpoint
- ✅ Twilio media downloads use basic auth

### Authentication
- Dashboard password-protected (simple auth for now)
- Consider adding JWT or session-based auth for production
- Rate limiting not yet implemented (add for production)

### CORS
- Configured to allow www.heymuze.app and *.vercel.app
- Localhost allowed for development
- Proper headers set for cross-origin requests

---

## Future Enhancements

### Planned Features
1. Multi-user admin support with proper auth
2. Analytics dashboard (message volume, costs, user growth)
3. Export corpus as JSON/PDF
4. API keys for programmatic access
5. Webhook for corpus updates (trigger external systems)
6. Speaker diarization for multi-person voice messages
7. Image support (describe and extract text from images)

### Scaling Considerations
- Add Redis for session management
- Implement background job queue (Celery/RQ) for transcription
- Add rate limiting per user
- Implement caching for corpus retrieval
- Consider CDN for dashboard assets

---

## Troubleshooting

### Common Issues

**"Corpus not updating"**
- Check Railway logs for errors
- Verify Gemini API key is valid
- Check if message triggered `should_update_corpus()` filters

**"Voice messages not transcribing"**
- Verify TWILIO_ACCOUNT_SID in env vars
- Check audio format is supported
- Review Railway logs for download errors

**"WhatsApp messages not reaching webhook"**
- Verify webhook URL in Twilio console
- Check Railway deployment is running
- Test webhook with Twilio debugger

**"Dashboard can't send messages"**
- Verify Twilio credentials in Vercel env vars
- Check /api/send-message route is working
- Review browser console for errors

---

## Support & Contact

- **GitHub**: https://github.com/Rickvdkommer/Muze
- **Issues**: Create issue on GitHub repo
- **Dashboard**: www.heymuze.app

---

*Last Updated: 2025-01-23*
*Version: 1.0.0*
