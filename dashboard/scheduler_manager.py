# dashboard/scheduler_manager.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()

def run_scheduled_scraping():
    """Task yang akan dijalankan oleh scheduler"""
    from dashboard.scheduler_views import scheduler_config, run_scraping_task, save_scheduler_config
    
    logger.info("=== SCHEDULED SCRAPING STARTED ===")
    
    if not scheduler_config.get('enabled', False):
        logger.info("Scheduler is disabled")
        return
    
    vendors = scheduler_config.get('vendors', [])
    keyword = scheduler_config.get('search_keyword', '')
    
    if not keyword or not vendors:
        logger.warning("No keyword or vendors configured")
        return
    
    logger.info(f"Running scheduler for keyword: '{keyword}', vendors: {vendors}")
    
    try:
        # Run the scraping task
        results = run_scraping_task(vendors, keyword)
        
        # Update last run time
        scheduler_config['last_run'] = timezone.now().isoformat()
        save_scheduler_config(scheduler_config)
        
        logger.info(f"=== SCHEDULED SCRAPING COMPLETED: {results} ===")
        return results
    except Exception as e:
        logger.error(f"Scheduled scraping failed: {e}", exc_info=True)

def update_scheduler(schedule_type, config):
    """Update APScheduler based on configuration"""
    
    # Remove existing jobs
    for job in scheduler.get_jobs():
        if job.id == 'scraping_scheduler':
            job.remove()
            logger.info("Removed existing schedule")
    
    if schedule_type == 'disabled':
        logger.info("Scheduler disabled")
        return
    
    # Add new job based on type
    if schedule_type == 'hourly':
        scheduler.add_job(
            run_scheduled_scraping,
            trigger=IntervalTrigger(hours=1),
            id='scraping_scheduler',
            name='Hourly Scraping',
            replace_existing=True
        )
        logger.info("Created hourly schedule")
        
    elif schedule_type == 'daily':
        scheduler.add_job(
            run_scheduled_scraping,
            trigger=CronTrigger(hour=0, minute=0),
            id='scraping_scheduler',
            name='Daily Scraping',
            replace_existing=True
        )
        logger.info("Created daily schedule at midnight")
        
    elif schedule_type == 'weekly':
        scheduler.add_job(
            run_scheduled_scraping,
            trigger=CronTrigger(day_of_week='mon', hour=0, minute=0),
            id='scraping_scheduler',
            name='Weekly Scraping',
            replace_existing=True
        )
        logger.info("Created weekly schedule on Monday")
        
    elif schedule_type == 'custom':
        interval = int(config.get('custom_interval', 1))
        unit = config.get('custom_unit', 'days')
        
        if unit == 'minutes':
            trigger = IntervalTrigger(minutes=interval)
        elif unit == 'hours':
            trigger = IntervalTrigger(hours=interval)
        elif unit == 'days':
            trigger = IntervalTrigger(days=interval)
        elif unit == 'weeks':
            trigger = IntervalTrigger(weeks=interval)
        else:
            trigger = IntervalTrigger(hours=1)
        
        scheduler.add_job(
            run_scheduled_scraping,
            trigger=trigger,
            id='scraping_scheduler',
            name='Custom Scraping',
            replace_existing=True
        )
        logger.info(f"Created custom schedule: every {interval} {unit}")

def get_next_run_time():
    """Get next scheduled run time"""
    for job in scheduler.get_jobs():
        if job.id == 'scraping_scheduler':
            return job.next_run_time
    return None

def start_scheduler():
    """Start the scheduler"""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")

def shutdown_scheduler():
    """Shutdown the scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler shutdown")