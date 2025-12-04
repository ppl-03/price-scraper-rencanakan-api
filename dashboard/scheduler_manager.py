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
    # PENTING: Import function, bukan variable
    from dashboard.scheduler_views import load_scheduler_config, run_scraping_task, save_scheduler_config
    
    logger.info("=== SCHEDULED SCRAPING STARTED ===")
    
    # LOAD CONFIG FRESH - INI YANG PENTING!
    config = load_scheduler_config()
    logger.info(f"Loaded fresh config: {config}")
    
    if not config.get('enabled', False):
        logger.warning("Scheduler is disabled in config")
        return
    
    vendors = config.get('vendors', [])
    keyword = config.get('search_keyword', '')
    
    if not keyword or not vendors:
        logger.warning(f"Missing data - Vendors: {vendors}, Keyword: '{keyword}'")
        return
    
    logger.info(f"Running scraping - Keyword: '{keyword}', Vendors: {vendors}")
    
    try:
        results = run_scraping_task(vendors, keyword)
        
        # Update last run time
        config['last_run'] = timezone.now().isoformat()
        save_scheduler_config(config)
        
        logger.info(f"=== SCRAPING COMPLETED: {results} ===")
        return results
    except Exception as e:
        logger.exception(f"Scraping failed: {e}")

def update_scheduler(schedule_type, config):
    """Update APScheduler based on configuration"""
    
    logger.info(f"=== UPDATE SCHEDULER ===")
    logger.info(f"Schedule type: {schedule_type}")
    logger.info(f"Config: {config}")
    
    # Remove existing jobs
    removed = False
    for job in scheduler.get_jobs():
        if job.id == 'scraping_scheduler':
            job.remove()
            removed = True
            logger.info("✓ Removed existing job")
    
    if not removed:
        logger.info("No existing job to remove")
    
    if schedule_type == 'disabled':
        logger.info("Scheduler disabled - no new job created")
        return
    
    # Add new job
    try:
        if schedule_type == 'hourly':
            scheduler.add_job(
                run_scheduled_scraping,
                trigger=IntervalTrigger(hours=1),
                id='scraping_scheduler',
                name='Hourly Scraping',
                replace_existing=True
            )
            logger.info("✓ Created HOURLY schedule")
            
        elif schedule_type == 'daily':
            scheduler.add_job(
                run_scheduled_scraping,
                trigger=CronTrigger(hour=0, minute=0),
                id='scraping_scheduler',
                name='Daily Scraping',
                replace_existing=True
            )
            logger.info("✓ Created DAILY schedule (midnight)")
            
        elif schedule_type == 'weekly':
            scheduler.add_job(
                run_scheduled_scraping,
                trigger=CronTrigger(day_of_week='mon', hour=0, minute=0),
                id='scraping_scheduler',
                name='Weekly Scraping',
                replace_existing=True
            )
            logger.info("✓ Created WEEKLY schedule (Monday midnight)")
            
        elif schedule_type == 'custom':
            interval = int(config.get('custom_interval', 1))
            unit = config.get('custom_unit', 'days')
            
            logger.info(f"Creating custom schedule: {interval} {unit}")
            
            if unit == 'minutes':
                trigger = IntervalTrigger(minutes=interval)
            elif unit == 'hours':
                trigger = IntervalTrigger(hours=interval)
            elif unit == 'days':
                trigger = IntervalTrigger(days=interval)
            elif unit == 'weeks':
                trigger = IntervalTrigger(weeks=interval)
            else:
                logger.error(f"Unknown unit: {unit}")
                return
            
            scheduler.add_job(
                run_scheduled_scraping,
                trigger=trigger,
                id='scraping_scheduler',
                name=f'Custom ({interval} {unit})',
                replace_existing=True
            )
            logger.info(f"✓ Created CUSTOM schedule: every {interval} {unit}")
        
        # Log all active jobs
        jobs = scheduler.get_jobs()
        logger.info(f"=== ACTIVE JOBS: {len(jobs)} ===")
        for job in jobs:
            logger.info(f"  ID: {job.id}")
            logger.info(f"  Name: {job.name}")
            logger.info(f"  Next run: {job.next_run_time}")
            logger.info(f"  Trigger: {job.trigger}")
            
    except Exception as e:
        logger.exception(f"Failed to create job: {e}")

def start_scheduler():
    """Start the scheduler"""
    if not scheduler.running:
        scheduler.start()
        logger.info("✓✓✓ APScheduler STARTED ✓✓✓")
    else:
        logger.info("APScheduler already running")
    
    # Log scheduler state
    logger.info(f"Scheduler running: {scheduler.running}")
    logger.info(f"Active jobs: {len(scheduler.get_jobs())}")

def get_scheduler_status():
    """Get scheduler status"""
    jobs = scheduler.get_jobs()
    return {
        'running': scheduler.running,
        'job_count': len(jobs),
        'jobs': [
            {
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            for job in jobs
        ]
    }