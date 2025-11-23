# Muze - Personal Biographer WhatsApp Bot

A WhatsApp bot that acts as your personal biographer, engaging in deep conversations and building a knowledge graph about your life using AI.

## Tech Stack

- **Framework:** Flask + Gunicorn
- **AI:** Google Gemini 2.0 Flash (via `google-genai`)
- **Messaging:** Twilio WhatsApp API
- **Deployment:** Railway.app
- **Python:** 3.12.3

## Project Structure

```
muze/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── runtime.txt           # Python version for Railway
├── Procfile              # Railway deployment config
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── user_corpus.md        # Auto-generated knowledge graph (created at runtime)
```

## Features

- **Conversational AI:** Muze engages in natural, empathetic conversations
- **Knowledge Graph:** Automatically organizes insights into structured categories
- **Context Awareness:** Remembers previous conversations to build deeper understanding
- **Follow-up Questions:** Always asks one thoughtful question to learn more
- **WhatsApp Integration:** Seamless messaging via Twilio

## Local Development

### 1. Clone and Setup

```bash
cd /Users/rickvandenkommer/Muze/Latest
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886

GEMINI_API_KEY=your_gemini_api_key

FLASK_ENV=development
PORT=5000
```

### 3. Run Locally

```bash
python app.py
```

The server will start at `http://localhost:5000`

### 4. Test Webhook Locally (with ngrok)

```bash
ngrok http 5000
```

Use the ngrok HTTPS URL for Twilio webhook configuration.

## Railway Deployment

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Muze personal biographer bot"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

### Step 2: Deploy to Railway

1. Go to [Railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect the Python app

### Step 3: Configure Environment Variables in Railway

Go to your project → Variables tab and add:

| Variable Name | Description | Example |
|--------------|-------------|---------|
| `GEMINI_API_KEY` | Your Google Gemini API key | `AIzaSy...` |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | `ACxxxxxxxx...` |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | `your_auth_token` |
| `TWILIO_PHONE_NUMBER` | Twilio WhatsApp number | `whatsapp:+14155238886` |
| `PORT` | Server port (Railway sets this automatically) | `5000` |
| `FLASK_ENV` | Flask environment | `production` |

### Step 4: Get Your Railway URL

After deployment, Railway will provide a public URL like:
```
https://your-app-name.up.railway.app
```

### Step 5: Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to Messaging → Settings → WhatsApp Sandbox (or your WhatsApp number)
3. Set the webhook URL to:
   ```
   https://your-app-name.up.railway.app/webhook
   ```
4. Set HTTP method to `POST`
5. Save configuration

## Getting API Keys

### Google Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Get API Key"
3. Create a new API key
4. Copy and add to Railway environment variables

### Twilio Setup

1. Sign up at [Twilio](https://www.twilio.com)
2. Get your Account SID and Auth Token from the dashboard
3. Enable WhatsApp by going to Messaging → Try it out → WhatsApp
4. For production, request WhatsApp Business approval

## Testing the Bot

1. Send a message to your Twilio WhatsApp number
2. Muze will respond and ask a follow-up question
3. Check Railway logs to monitor conversations:
   ```bash
   railway logs
   ```

## Knowledge Graph Structure

The bot automatically creates and maintains `user_corpus.md` with these sections:

- **Worldview:** Core beliefs and perspectives
- **Personal History:** Life events and experiences
- **Values & Beliefs:** What matters most
- **Goals & Aspirations:** Future plans and dreams
- **Relationships:** Important people and connections
- **Interests & Hobbies:** Passions and activities

## Monitoring & Logs

View real-time logs in Railway:

```bash
railway logs --follow
```

Or in the Railway dashboard under the Logs tab.

## Health Checks

The app includes health check endpoints:

- `GET /health` - Returns service status
- `GET /` - Returns API information

## Troubleshooting

**Issue:** `google-genai` import errors
- **Solution:** Ensure you're using `google-genai` (NOT `google-generativeai`)

**Issue:** Twilio webhook not receiving messages
- **Solution:** Verify webhook URL is HTTPS and points to `/webhook`

**Issue:** Gemini API errors
- **Solution:** Check API key is valid and has quota remaining

**Issue:** Railway deployment fails
- **Solution:** Check Railway build logs and ensure all environment variables are set

## Cost Considerations

- **Railway:** Free tier available, then pay-as-you-go
- **Gemini API:** Free tier: 15 requests/minute, paid plans available
- **Twilio:** WhatsApp messages cost $0.005/message (check current pricing)

## Security Notes

- Never commit `.env` file to Git
- Keep API keys secure
- Use Railway environment variables for sensitive data
- The `user_corpus.md` contains personal information - ensure it's in `.gitignore`

## Future Enhancements

- Add user authentication for multi-user support
- Implement vector database for better context retrieval
- Add export functionality (PDF, JSON)
- Scheduled check-ins and reminders
- Voice message support
- Multi-language support

## License

MIT License - feel free to modify and use for your own projects.

## Support

For issues or questions:
- Check Railway logs for error details
- Review Twilio webhook logs
- Verify environment variables are correctly set

---

Built with Flask, Gemini AI, and Twilio for Railway deployment.
