from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    
    def ready(self):
        # Import and start scheduler
        from dashboard import scheduler_manager
        scheduler_manager.start_scheduler()
        
        # Load and apply saved schedule
        from dashboard.scheduler_views import load_scheduler_config
        config = load_scheduler_config()
        if config.get('enabled'):
            scheduler_manager.update_scheduler(
                config.get('schedule_type'),
                config
            )
