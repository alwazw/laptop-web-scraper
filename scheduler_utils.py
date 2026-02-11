from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import subprocess
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_job(script_name):
    logger.info(f"Starting scheduled job: {script_name} at {datetime.now()}")
    try:
        subprocess.run([sys.executable, script_name], check=True)
        logger.info(f"Successfully completed scheduled job: {script_name}")
    except Exception as e:
        logger.error(f"Error in scheduled job {script_name}: {e}")

def start_scheduler():
    if not scheduler.running:
        # Example: Run every day at 2 AM
        scheduler.add_job(run_job, CronTrigger(hour=2, minute=0), args=['main.py'], id='daily_scrape')
        scheduler.start()
        logger.info("Scheduler started background threads.")

def get_jobs():
    return scheduler.get_jobs()
