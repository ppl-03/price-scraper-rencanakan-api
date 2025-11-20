from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import json
import logging

from api.gemilang.scheduler import GemilangScheduler
from api.depobangunan.scheduler import DepoBangunanScheduler
from api.juragan_material.scheduler import JuraganMaterialScheduler
from api.mitra10.scheduler import Mitra10Scheduler
from api.tokopedia.scheduler import TokopediaScheduler

logger = logging.getLogger(__name__)

# Store scheduler configuration (in production, use database)
scheduler_config = {
    'enabled': False,
    'schedule_type': 'disabled',  # disabled, hourly, daily, weekly, custom
    'custom_interval': 1,
    'custom_unit': 'days',
    'custom_time': '00:00',
    'custom_days': [],
    'vendors': ['gemilang', 'depobangunan', 'juragan_material', 'mitra10', 'tokopedia'],
    'pages_per_keyword': 1,
    'last_run': None,
    'next_run': None
}

AVAILABLE_VENDORS = {
    'gemilang': {'name': 'Gemilang', 'scheduler': GemilangScheduler},
    'depobangunan': {'name': 'Depo Bangunan', 'scheduler': DepoBangunanScheduler},
    'juragan_material': {'name': 'Juragan Material', 'scheduler': JuraganMaterialScheduler},
    'mitra10': {'name': 'Mitra10', 'scheduler': Mitra10Scheduler},
    'tokopedia': {'name': 'Tokopedia', 'scheduler': TokopediaScheduler},
}

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
        
        # Validate schedule type
        valid_types = ['disabled', 'hourly', 'daily', 'weekly', 'custom']
        if schedule_type not in valid_types:
            messages.error(request, f'Invalid schedule type: {schedule_type}')
            return redirect('dashboard:scheduler_settings')
        
        # Update configuration
        scheduler_config['schedule_type'] = schedule_type
        scheduler_config['enabled'] = schedule_type != 'disabled'
        
        # Update custom schedule settings if provided
        if schedule_type == 'custom':
            try:
                interval = int(request.POST.get('custom_interval', 1))
                scheduler_config['custom_interval'] = max(1, interval)
            except ValueError:
                scheduler_config['custom_interval'] = 1
            
            scheduler_config['custom_unit'] = request.POST.get('custom_unit', 'days')
            scheduler_config['custom_time'] = request.POST.get('custom_time', '00:00')
            scheduler_config['custom_days'] = request.POST.getlist('custom_days')
        
        # Update vendor selection
        selected_vendors = request.POST.getlist('vendors')
        if selected_vendors:
            scheduler_config['vendors'] = selected_vendors
        
        # Update pages per keyword
        try:
            pages = int(request.POST.get('pages_per_keyword', 1))
            scheduler_config['pages_per_keyword'] = max(1, pages)
        except ValueError:
            scheduler_config['pages_per_keyword'] = 1
        
        # Create human-readable message
        if schedule_type == 'custom':
            interval = scheduler_config['custom_interval']
            unit = scheduler_config['custom_unit']
            time = scheduler_config['custom_time']
            schedule_msg = f'Custom: Every {interval} {unit}'
            if unit in ['days', 'weeks']:
                schedule_msg += f' at {time}'
        else:
            schedule_msg = schedule_type.title()
        
        messages.success(
            request, 
            f'Scheduler updated to: {schedule_msg}'
        )
        logger.info(f'Scheduler configuration updated: {scheduler_config}')
        
    except Exception as e:
        messages.error(request, f'Failed to update scheduler: {str(e)}')
        logger.error(f'Scheduler update error: {e}', exc_info=True)
    
    return redirect('dashboard:scheduler_settings')

@require_POST
def run_scheduler_now(request):
    """Manually trigger scheduler run"""
    try:
        vendors = scheduler_config.get('vendors', [])
        pages = scheduler_config.get('pages_per_keyword', 1)
        
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
                    pages_per_keyword=pages
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
        
        scheduler_config['last_run'] = timezone.now().isoformat()
        
        messages.success(request, 'Scheduler run completed')
        return JsonResponse({
            'success': True,
            'results': results,
            'timestamp': scheduler_config['last_run']
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
    return JsonResponse({
        'enabled': scheduler_config['enabled'],
        'schedule_type': scheduler_config['schedule_type'],
        'vendors': scheduler_config['vendors'],
        'last_run': scheduler_config.get('last_run'),
        'next_run': scheduler_config.get('next_run'),
        'server_time': timezone.now().isoformat()
    })
