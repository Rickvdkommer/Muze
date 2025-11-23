"""
Background scheduler for proactive nudges.
Runs every hour to process the nudge dispatch queue.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def process_nudges_job():
    """
    Job function that runs every hour to process nudges.
    This is called by APScheduler.
    """
    try:
        from scheduler_dispatcher import SchedulerDispatcher
        from google import genai
        from twilio.rest import Client as TwilioClient
        import os

        # Initialize clients
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
        TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
        TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

        client = genai.Client(api_key=GEMINI_API_KEY)
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Initialize dispatcher
        dispatcher = SchedulerDispatcher(client, twilio_client, TWILIO_PHONE_NUMBER)

        # Process queue
        logger.info("🔄 Starting scheduled nudge processing...")
        result = dispatcher.process_dispatch_queue()
        logger.info(f"✅ Nudge processing complete: {result['sent']} sent, {result['skipped']} skipped")

    except Exception as e:
        logger.error(f"❌ Error in scheduled nudge processing: {str(e)}", exc_info=True)


def start_scheduler():
    """
    Initialize and start the background scheduler.
    Called when Flask app starts.
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running, skipping initialization")
        return scheduler

    logger.info("🚀 Initializing background scheduler for proactive nudges...")

    scheduler = BackgroundScheduler(daemon=True)

    # Schedule nudge processing every hour at minute 0
    # Cron format: minute hour day month day_of_week
    scheduler.add_job(
        func=process_nudges_job,
        trigger=CronTrigger(minute=0, hour='*'),  # Every hour at :00
        id='process_nudges',
        name='Process Proactive Nudges',
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )

    # Start the scheduler
    scheduler.start()
    logger.info("✅ Scheduler started successfully - nudges will run every hour")

    # Shut down scheduler gracefully on app exit
    atexit.register(lambda: scheduler.shutdown(wait=False))

    return scheduler


def stop_scheduler():
    """
    Stop the background scheduler.
    """
    global scheduler
    if scheduler is not None:
        logger.info("Stopping scheduler...")
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("✅ Scheduler stopped")
