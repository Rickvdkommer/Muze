# Muze API Documentation

Backend infrastructure for storing messages and managing user knowledge graphs.

## Database Schema

### Tables:

**users**
- `phone_number` (PRIMARY KEY) - WhatsApp number with prefix (e.g., "whatsapp:+31634829116")
- `display_name` - Optional display name
- `created_at` - Account creation timestamp
- `last_message_at` - Last message timestamp

**messages**
- `id` (AUTO INCREMENT)
- `phone_number` (FOREIGN KEY → users)
- `direction` - "incoming" or "outgoing"
- `message_text` - Message content
- `timestamp` - Message timestamp
- `processed` - Boolean (for human-in-the-loop queue)

**user_corpus**
- `phone_number` (PRIMARY KEY, FOREIGN KEY → users)
- `corpus_markdown` - Full markdown knowledge graph
- `last_updated` - Last update timestamp

---

## API Endpoints

### 1. Webhook (Twilio Integration)

**POST** `/webhook`

Receives incoming WhatsApp messages and stores them in the database.

**Note:** Currently does NOT auto-respond (human-in-the-loop mode).

---

### 2. Get User Messages

**GET** `/api/users/<phone_number>/messages?limit=50`

Get message history for a specific user.

**Parameters:**
- `phone_number` - User's phone number (with or without "whatsapp:" prefix)
- `limit` (optional) - Number of messages to retrieve (default: 50)

**Example:**
```bash
curl https://your-app.railway.app/api/users/whatsapp:+31634829116/messages?limit=20
```

**Response:**
```json
{
  "phone_number": "whatsapp:+31634829116",
  "message_count": 5,
  "messages": [
    {
      "id": 1,
      "direction": "incoming",
      "text": "Hello Muze!",
      "timestamp": "2025-11-23T16:30:00",
      "processed": false
    }
  ]
}
```

---

### 3. Get User Corpus

**GET** `/api/users/<phone_number>/corpus`

Retrieve the markdown knowledge graph for a user.

**Example:**
```bash
curl https://your-app.railway.app/api/users/whatsapp:+31634829116/corpus
```

**Response:**
```json
{
  "phone_number": "whatsapp:+31634829116",
  "corpus": "# Personal Knowledge Graph\n\n## Worldview\n..."
}
```

---

### 4. Update User Corpus

**PUT** `/api/users/<phone_number>/corpus`

Update the markdown knowledge graph for a user.

**Body:**
```json
{
  "corpus": "# Personal Knowledge Graph\n\n## Worldview\nUpdated information..."
}
```

**Example:**
```bash
curl -X PUT https://your-app.railway.app/api/users/whatsapp:+31634829116/corpus \
  -H "Content-Type: application/json" \
  -d '{"corpus": "# Updated corpus..."}'
```

---

### 5. Get Unprocessed Messages

**GET** `/api/messages/unprocessed?limit=10`

Get messages that haven't been processed yet (human-in-the-loop queue).

**Parameters:**
- `limit` (optional) - Number of messages to retrieve (default: 10)

**Example:**
```bash
curl https://your-app.railway.app/api/messages/unprocessed
```

**Response:**
```json
{
  "count": 3,
  "messages": [
    {
      "id": 5,
      "phone_number": "whatsapp:+31634829116",
      "text": "What's your favorite book?",
      "timestamp": "2025-11-23T16:45:00"
    }
  ]
}
```

---

### 6. Mark Message as Processed

**POST** `/api/messages/<message_id>/process`

Mark a message as processed after human review.

**Example:**
```bash
curl -X POST https://your-app.railway.app/api/messages/5/process
```

**Response:**
```json
{
  "message": "Message marked as processed",
  "message_id": 5
}
```

---

### 7. Generate AI Response

**POST** `/api/generate-response`

Generate a suggested AI response for a given message (for human reviewer to approve/edit).

**Body:**
```json
{
  "phone_number": "whatsapp:+31634829116",
  "message": "I've been thinking about changing careers"
}
```

**Example:**
```bash
curl -X POST https://your-app.railway.app/api/generate-response \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "whatsapp:+31634829116", "message": "I love hiking"}'
```

**Response:**
```json
{
  "response": "That's wonderful! Hiking is a great way to connect with nature. What draws you to hiking specifically - is it the physical challenge, the solitude, or something else?",
  "phone_number": "whatsapp:+31634829116"
}
```

---

## Railway Setup

### Required Environment Variables:

Add these in Railway Dashboard → Variables:

```
DATABASE_URL=postgresql://user:password@host:5432/database
GEMINI_API_KEY=AIzaSy...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
FLASK_ENV=production
```

### Adding PostgreSQL to Railway:

1. Go to your Railway project
2. Click **"+ New"** → **Database** → **PostgreSQL**
3. Railway auto-creates `DATABASE_URL` environment variable
4. Your app will automatically connect to it

---

## Workflow Example

### Human-in-the-Loop Flow:

1. **User sends WhatsApp message** → Stored in DB (not processed)
2. **Admin checks unprocessed messages:**
   ```bash
   GET /api/messages/unprocessed
   ```
3. **Admin generates AI response:**
   ```bash
   POST /api/generate-response
   Body: {"phone_number": "...", "message": "..."}
   ```
4. **Admin reviews/edits response** (in your admin panel)
5. **Admin sends response via Twilio API** (manually or via your admin panel)
6. **Mark message as processed:**
   ```bash
   POST /api/messages/5/process
   ```

---

## Testing Locally

### 1. Set up PostgreSQL locally:

```bash
# Using Docker
docker run --name muze-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres

# Set DATABASE_URL in .env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/muze
```

### 2. Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Run the app:

```bash
python app.py
```

### 4. Test endpoints:

```bash
# Get unprocessed messages
curl http://localhost:5000/api/messages/unprocessed

# Get user corpus
curl http://localhost:5000/api/users/whatsapp:+31634829116/corpus
```

---

## Next Steps

1. Build admin dashboard to:
   - View unprocessed messages
   - Generate AI responses
   - Approve/edit responses
   - Send responses via Twilio

2. Add authentication to API endpoints

3. Add webhook for outgoing message delivery status

4. Implement corpus auto-update with Gemini after each conversation
