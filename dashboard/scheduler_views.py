from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import json
import logging
import os

from api.gemilang.scheduler import GemilangScheduler
from api.depobangunan.scheduler import DepoBangunanScheduler
from api.juragan_material.scheduler import JuraganMaterialScheduler
from api.mitra10.scheduler import Mitra10Scheduler
from api.tokopedia.scheduler import TokopediaScheduler

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'scheduler_config.json')

def load_scheduler_config():
    """Load config from JSON file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info(f"Config loaded from file: {config}")
                return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    # Default config
    default_config = {
        'enabled': False,
        'schedule_type': 'disabled',
        'custom_interval': 1,
        'custom_unit': 'days',
        'custom_time': '00:00',
        'custom_days': [],
        'vendors': [],
        'search_keyword': '',
        'last_run': None,
        'next_run': None
    }
    logger.info("Using default config")
    return default_config

def save_scheduler_config(config):
    """Save config to JSON file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info(f"Config saved to file: {config}")
    except Exception as e:
        logger.error(f"Error saving config: {e}")

# Load config at module level
scheduler_config = load_scheduler_config()


AVAILABLE_VENDORS = {
    'gemilang': {'name': 'Gemilang', 'scheduler': GemilangScheduler},
    'depobangunan': {'name': 'Depo Bangunan', 'scheduler': DepoBangunanScheduler},
    'juragan_material': {'name': 'Juragan Material', 'scheduler': JuraganMaterialScheduler},
    'mitra10': {'name': 'Mitra10', 'scheduler': Mitra10Scheduler},
    'tokopedia': {'name': 'Tokopedia', 'scheduler': TokopediaScheduler},
}

def run_scraping_task(vendors, keyword):
    """Run scraping task for given vendors and keyword"""
    results = {}
    
    for vendor_key in vendors:
        vendor_info = AVAILABLE_VENDORS.get(vendor_key)
        if not vendor_info:
            logger.warning(f"Unknown vendor: {vendor_key}")
            continue
        
        try:
            # Import scheduler class dynamically
            if vendor_key == 'gemilang':
                from api.gemilang.scheduler import GemilangScheduler
                scheduler_class = GemilangScheduler
            elif vendor_key == 'depobangunan':
                from api.depobangunan.scheduler import DepoBangunanScheduler
                scheduler_class = DepoBangunanScheduler
            elif vendor_key == 'juragan_material':
                from api.juragan_material.scheduler import JuraganMaterialScheduler
                scheduler_class = JuraganMaterialScheduler
            elif vendor_key == 'mitra10':
                from api.mitra10.scheduler import Mitra10Scheduler
                scheduler_class = Mitra10Scheduler
            elif vendor_key == 'tokopedia':
                from api.tokopedia.scheduler import TokopediaScheduler
                scheduler_class = TokopediaScheduler
            else:
                logger.warning(f"No scheduler class for {vendor_key}")
                continue
            
            scheduler = scheduler_class()
            
            logger.info(f"Running scheduler for {vendor_key} with keyword '{keyword}'")
            
            summary = scheduler.run(
                server_time=timezone.now(),
                vendors=[vendor_key],
                search_keyword=keyword
            )
            
            vendor_summary = summary.get('vendors', {}).get(vendor_key, {})
            results[vendor_key] = {
                'status': vendor_summary.get('status', 'unknown'),
                'products_found': vendor_summary.get('products_found', 0),
                'saved': vendor_summary.get('saved', 0),
            }
            
            logger.info(f"Results for {vendor_key}: {results[vendor_key]}")
            
        except Exception as e:
            logger.error(f'Error running scheduler for {vendor_key}: {e}', exc_info=True)
            results[vendor_key] = {
                'status': 'error',
                'error': str(e)
            }
    
    return results

@require_GET
def scheduler_settings(request):
    """Display scheduler configuration page"""
    context = {
        'config': scheduler_config,
        'available_vendors': AVAILABLE_VENDORS,
        'server_time': timezone.now(),
    }
    return render(request, 'dashboard/scheduler_settings.html', context)

@require_POST
def update_schedule(request):
    """Update scheduler configuration"""
    try:
        schedule_type = request.POST.get('schedule_type', 'disabled')
        vendors = request.POST.getlist('vendors')
        search_keyword = request.POST.get('search_keyword', '').strip()
        
        if not search_keyword:
            messages.error(request, 'Search keyword is required!')
            return redirect('dashboard:scheduler_settings')
        
        # Update config
        scheduler_config['schedule_type'] = schedule_type
        scheduler_config['vendors'] = vendors
        scheduler_config['search_keyword'] = search_keyword
        scheduler_config['enabled'] = schedule_type != 'disabled'
        
        if schedule_type == 'custom':
            scheduler_config['custom_interval'] = request.POST.get('custom_interval', '1')
            scheduler_config['custom_unit'] = request.POST.get('custom_unit', 'days')
        
        # SAVE TO FILE
        save_scheduler_config(scheduler_config)
        
        # UPDATE APSCHEDULER
        from dashboard.scheduler_manager import update_scheduler
        update_scheduler(schedule_type, scheduler_config)
        
        messages.success(request, f'Schedule updated to: {schedule_type}')
        
    except Exception as e:
        messages.error(request, f'Failed to update scheduler: {str(e)}')
        logger.error(f'Scheduler update error: {e}', exc_info=True)
    
    return redirect('dashboard:scheduler_settings')

@require_POST
def run_scheduler_now(request):
    """Manually trigger scheduler run"""
    try:
        formdata = request.POST.dict()
        vendors = request.POST.getlist('vendors')
        keyword = formdata.get('search_keyword')
        results = {}
        for vendor_key in vendors:
            vendor_info = AVAILABLE_VENDORS.get(vendor_key)
            if not vendor_info:
                continue
            
            try:
                scheduler_class = vendor_info['scheduler']
                scheduler = scheduler_class()
                
                # Run the scheduler with the correct parameters
                summary = scheduler.run(
                    server_time=timezone.now(),
                    vendors=[vendor_key],
                    search_keyword=keyword
                )
                
                vendor_summary = summary.get('vendors', {}).get(vendor_key, {})
                results[vendor_key] = {
                    'status': vendor_summary.get('status', 'unknown'),
                    'products_found': vendor_summary.get('products_found', 0),
                    'saved': vendor_summary.get('saved', 0),
                }
                
                
                
            except Exception as e:
                results[vendor_key] = {
                    'status': 'error',
                    'error': str(e)
                }
                logger.error(f'Error running scheduler for {vendor_key}: {e}')
        
        formdata['last_run'] = timezone.now().isoformat()
        
        messages.success(request, 'Scheduler run completed')
        return JsonResponse({
            'success': True,
            'results': results,
            'timestamp': formdata['last_run']
        })
        
    except Exception as e:
        messages.error(request, f'Scheduler run failed: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_GET
def get_scheduler_status(request):
    """Get current scheduler status"""
    from dashboard.scheduler_manager import get_next_run_time
    
    next_run = get_next_run_time()
    
    return JsonResponse({
        'enabled': scheduler_config.get('enabled', False),
        'schedule_type': scheduler_config.get('schedule_type', 'disabled'),
        'keyword': scheduler_config.get('search_keyword', ''),
        'vendors': scheduler_config.get('vendors', []),
        'last_run': scheduler_config.get('last_run'),
        'next_run': next_run.isoformat() if next_run else None,
        'server_time': timezone.now().isoformat()
    })