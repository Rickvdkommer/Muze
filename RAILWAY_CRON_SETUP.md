# Railway Cron Job Setup Guide

This guide walks you through setting up the proactive nudge system using Railway's built-in Cron Jobs feature.

## Step 1: Generate a Secret Token

First, generate a secure random token for authentication:

```bash
# On Mac/Linux, run this in terminal:
openssl rand -hex 32
```

Copy the output (it will look like: `a1b2c3d4e5f6...`)

## Step 2: Add Environment Variable to Railway

1. Go to your Railway project dashboard
2. Click on your **Muze** service
3. Go to the **Variables** tab
4. Click **+ New Variable**
5. Add:
   - **Name:** `CRON_SECRET_TOKEN`
   - **Value:** [paste the token you generated above]
6. Click **Add**

Railway will automatically redeploy your app with the new variable.

## Step 3: Create a Cron Job in Railway

### Option A: Using Railway Dashboard (Recommended)

1. In your Railway project, click **+ New** → **Cron Job**
2. Configure the cron job:
   - **Name:** `Proactive Nudges`
   - **Schedule:** `0 * * * *` (every hour at :00 minutes)
   - **Command:** Leave empty (we'll use HTTP request instead)
   - **Service:** Select your main Muze service
3. Under **HTTP Request** section:
   - **Method:** POST
   - **URL:** `https://${{RAILWAY_PUBLIC_DOMAIN}}/api/cron/process-nudges`
   - **Headers:** Click **+ Add Header**
     - **Key:** `X-Cron-Secret`
     - **Value:** `${{CRON_SECRET_TOKEN}}`
4. Click **Deploy**

### Option B: Using railway.toml (Alternative)

If you prefer configuration as code, create `railway.toml` in your project root:

```toml
[deploy]
startCommand = "gunicorn app:app"

[[crons]]
name = "proactive-nudges"
schedule = "0 * * * *"
command = "curl -X POST https://$RAILWAY_PUBLIC_DOMAIN/api/cron/process-nudges -H 'X-Cron-Secret: $CRON_SECRET_TOKEN'"
```

Then commit and push:
```bash
git add railway.toml
git commit -m "Add Railway cron configuration"
git push origin main
```

## Step 4: Verify the Setup

### Test Manually First

Before waiting for the hourly trigger, test the endpoint manually:

```bash
# Replace YOUR_APP_URL with your Railway app URL
# Replace YOUR_SECRET_TOKEN with your actual token

curl -X POST https://YOUR_APP_URL.railway.app/api/cron/process-nudges \
  -H "X-Cron-Secret: YOUR_SECRET_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected response:**
```json
{
  "status": "success",
  "sent": 0,
  "skipped": 2
}
```

### Monitor the Cron Job

1. Go to Railway Dashboard → Your Project → Cron Jobs tab
2. You'll see the "Proactive Nudges" job listed
3. Wait for the next hour mark (e.g., 3:00 PM, 4:00 PM)
4. Check the **Deployments** log for your main service
5. Look for these log entries:
   ```
   === CRON: Process Nudges Triggered ===
   === CRON: Complete - Sent X, Skipped Y ===
   ```

## Cron Schedule Reference

The schedule `0 * * * *` means:
- **Minute:** 0 (at the top of the hour)
- **Hour:** * (every hour)
- **Day:** * (every day)
- **Month:** * (every month)
- **Weekday:** * (every day of week)

**Result:** Runs at 12:00, 1:00, 2:00, 3:00, etc. (every hour on the hour)

### Alternative Schedules

If you want to adjust the frequency:

```bash
# Every 2 hours
0 */2 * * *

# Every 4 hours
0 */4 * * *

# Every day at 9 AM, 1 PM, and 5 PM
0 9,13,17 * * *

# Every 30 minutes
*/30 * * * *
```

## Troubleshooting

### Cron job returns 401 Unauthorized

- **Cause:** The `X-Cron-Secret` header doesn't match `CRON_SECRET_TOKEN`
- **Fix:** Double-check that the token in Railway Variables matches the one in your cron job header

### Cron job isn't triggering

- **Check:** Go to Railway Dashboard → Cron Jobs → View execution history
- **Check:** Verify the schedule syntax is correct
- **Check:** Ensure your main service is running (not sleeping)

### No nudges being sent (sent: 0)

This is normal if:
- All users are in quiet hours
- No open loops have decayed yet
- Last interaction was too recent (pacing rules)
- All upcoming events were already checked recently

Check the logs for detailed reasoning:
```
Skipped user whatsapp:+123456789 - in quiet hours
Skipped user whatsapp:+987654321 - no candidates
```

## Security Notes

- The `CRON_SECRET_TOKEN` prevents unauthorized triggering of the endpoint
- Keep this token secret - don't commit it to version control
- Railway variables are encrypted and only accessible to your services
- If the token is compromised, generate a new one and update both Railway Variable and Cron Job header

## Next Steps

Once the cron job is working:

1. **Monitor the first few executions** to ensure nudges are being sent appropriately
2. **Check user feedback** - are the proactive messages helpful or annoying?
3. **Adjust pacing rules** in `scheduler_dispatcher.py` if needed (currently 4h/24h/48h)
4. **Tune quiet hours** per user in the admin dashboard
5. **Review open loops** to ensure they're being tracked correctly

Your proactive intelligence system is now fully automated! 🎉
