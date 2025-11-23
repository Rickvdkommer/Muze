# Muze Admin Dashboard

Human-in-the-loop management interface for the Muze Personal Biographer bot.

## Features

- **Message Queue**: View all unprocessed WhatsApp messages
- **AI Response Generation**: Auto-generate suggested responses using Gemini AI
- **Response Editor**: Edit and approve AI responses before sending
- **User Corpus Viewer**: View and edit user knowledge graphs
- **Simple Authentication**: Password-protected admin access
- **Real-time Updates**: Auto-refresh message queue every 30 seconds

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Authentication**: Simple password (cookie-based)
- **API Client**: Axios
- **Deployment**: Vercel

## Local Development

### 1. Install Dependencies

```bash
cd dashboard
npm install
```

### 2. Configure Environment Variables

Create `.env.local` file:

```env
# Backend API URL (Railway deployment)
NEXT_PUBLIC_API_URL=https://your-railway-app.up.railway.app

# Admin password
ADMIN_PASSWORD=your_secure_password_here

# Twilio credentials (for sending responses)
NEXT_PUBLIC_TWILIO_ACCOUNT_SID=ACxxxxxxxx
NEXT_PUBLIC_TWILIO_AUTH_TOKEN=your_auth_token
NEXT_PUBLIC_TWILIO_PHONE_NUMBER=whatsapp:+14155238886
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Vercel Deployment

### Method 1: Deploy from GitHub (Recommended)

1. **Push to GitHub** (already done if you're reading this)

2. **Go to Vercel**:
   - Visit [vercel.com](https://vercel.com)
   - Click "Add New Project"
   - Import your GitHub repository: `Rickvdkommer/Muze`

3. **Configure Project**:
   - **Framework Preset**: Next.js
   - **Root Directory**: `dashboard` ← IMPORTANT!
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

4. **Add Environment Variables** in Vercel Dashboard:
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-app.up.railway.app
   ADMIN_PASSWORD=your_secure_password
   NEXT_PUBLIC_TWILIO_ACCOUNT_SID=ACxxxxxxxx
   NEXT_PUBLIC_TWILIO_AUTH_TOKEN=xxxxxxxx
   NEXT_PUBLIC_TWILIO_PHONE_NUMBER=whatsapp:+14155238886
   ```

5. **Deploy**: Click "Deploy"

### Method 2: Deploy via Vercel CLI

```bash
cd dashboard
npm install -g vercel
vercel
```

Follow the prompts and set environment variables when asked.

## Custom Domain Setup (heymuze.app)

### In Vercel:

1. Go to your project → **Settings** → **Domains**
2. Click "Add Domain"
3. Enter: `www.heymuze.app`
4. Vercel will provide DNS records

### In Your Domain Registrar:

Add these DNS records (exact values shown in Vercel):

**For www.heymuze.app:**
```
Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

**For heymuze.app (root domain):**
```
Type: A
Name: @
Value: 76.76.21.21
```

**Or alternatively:**
```
Type: CNAME
Name: @
Value: cname.vercel-dns.com
```

### Verify:

- Wait 5-10 minutes for DNS propagation
- Visit [www.heymuze.app](http://www.heymuze.app)
- Should redirect to HTTPS automatically

## Usage

### Login

1. Visit your dashboard URL
2. Enter admin password (set in environment variables)
3. Click "Sign In"

### Process Messages

1. **View Queue**: See all unprocessed messages in the left panel
2. **Select Message**: Click on a message to view details
3. **Review AI Response**: Auto-generated response appears
4. **Edit Response**: Modify the response as needed
5. **Send**: Click "Send Response" to send via WhatsApp
6. **Skip**: Click "Skip" to mark as processed without sending

### View User Corpus

1. Click "Users & Corpus" tab
2. Enter phone number (with or without `whatsapp:` prefix)
3. Click "Load"
4. View the markdown knowledge graph
5. Click "Edit Corpus" to modify
6. Click "Save Changes" when done

## Security Notes

- **Password Protection**: Simple password auth via environment variable
- **HTTPS Only**: Vercel provides SSL automatically
- **Cookies**: Authentication stored in HTTP-only cookies (24hr expiry)
- **No Public API**: Dashboard communicates with Railway backend

## Environment Variables Reference

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `NEXT_PUBLIC_API_URL` | Railway backend URL | Yes | `https://muze.up.railway.app` |
| `ADMIN_PASSWORD` | Dashboard login password | Yes | `your-secure-password` |
| `NEXT_PUBLIC_TWILIO_ACCOUNT_SID` | Twilio Account SID | Yes | `AC...` |
| `NEXT_PUBLIC_TWILIO_AUTH_TOKEN` | Twilio Auth Token | Yes | `...` |
| `NEXT_PUBLIC_TWILIO_PHONE_NUMBER` | WhatsApp sender number | Yes | `whatsapp:+14155...` |

## Troubleshooting

### "Failed to load messages"
- Check `NEXT_PUBLIC_API_URL` points to Railway backend
- Verify Railway app is running (`/health` endpoint)
- Check browser console for CORS errors

### "Failed to send message"
- Verify Twilio credentials are correct
- Check Twilio account has WhatsApp enabled
- Ensure phone number includes `whatsapp:` prefix

### "Invalid password"
- Verify `ADMIN_PASSWORD` environment variable is set correctly
- Clear cookies and try again

### Domain not working
- DNS propagation can take up to 48 hours
- Verify DNS records match Vercel's requirements
- Use `dig www.heymuze.app` to check DNS

## Project Structure

```
dashboard/
├── app/
│   ├── api/auth/          # Password authentication endpoint
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Main page (login/dashboard router)
│   └── globals.css        # Global styles
├── components/
│   ├── Dashboard.tsx      # Main dashboard container
│   ├── LoginPage.tsx      # Login form
│   ├── MessageQueue.tsx   # Unprocessed messages list
│   ├── MessageDetail.tsx  # Message detail + AI response
│   └── UserCorpusViewer.tsx  # Corpus viewer/editor
├── lib/
│   ├── api.ts            # Backend API client
│   └── auth.ts           # Authentication utilities
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

## Future Enhancements

- [ ] Add proper user authentication (NextAuth.js)
- [ ] Add message search and filtering
- [ ] Add analytics dashboard
- [ ] Add corpus auto-update after sending response
- [ ] Add message templates
- [ ] Add bulk actions
- [ ] Add user tagging and segmentation

## Support

For issues or questions, check the main Muze repository README or Railway/Vercel logs.

---

Built with Next.js and deployed on Vercel.
