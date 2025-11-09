from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
from db_pricing.utils import check_database_connection, check_gemilang_table_exists
from db_pricing.models import PriceAnomaly
from db_pricing.anomaly_service import PriceAnomalyService
import json
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def check_database_status(request):
    connection_result = check_database_connection()
    table_result = check_gemilang_table_exists()
    
    response_data = {
        'connection': {
            'connected': connection_result['connected'],
            'database': connection_result['database'],
            'host': connection_result['host'],
            'error': connection_result['error']
        },
        'gemilang_table': {
            'exists': table_result['exists'],
            'columns': table_result['columns'],
            'error': table_result['error']
        },
        'overall_status': 'healthy' if (connection_result['connected'] and table_result['exists']) else 'unhealthy'
    }
    
    status_code = 200 if response_data['overall_status'] == 'healthy' else 503
    
    return JsonResponse(response_data, status=status_code)


# ==================== PRICE ANOMALY VIEWS ====================

@require_http_methods(["GET"])
def list_price_anomalies(request):
    """
    List price anomalies with filtering and pagination
    
    Query parameters:
    - status: Filter by status (pending, reviewed, approved, rejected)
    - vendor: Filter by vendor (gemilang, mitra10, tokopedia, depobangunan, juragan_material)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - search: Search in product name
    """
    try:
        # Get query parameters
        status = request.GET.get('status', None)
        vendor = request.GET.get('vendor', None)
        page_num = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)
        search = request.GET.get('search', '').strip()
        
        # Build queryset
        queryset = PriceAnomaly.objects.all()
        
        # Apply filters
        if status:
            queryset = queryset.filter(status=status)
        
        if vendor:
            queryset = queryset.filter(vendor=vendor)
        
        if search:
            queryset = queryset.filter(product_name__icontains=search)
        
        # Order by newest first
        queryset = queryset.order_by('-detected_at')
        
        # Paginate
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(page_num)
        
        # Serialize anomalies
        anomalies = [
            {
                'id': anomaly.id,
                'vendor': anomaly.vendor,
                'product_name': anomaly.product_name,
                'product_url': anomaly.product_url,
                'unit': anomaly.unit,
                'location': anomaly.location,
                'old_price': anomaly.old_price,
                'new_price': anomaly.new_price,
                'change_percent': float(anomaly.change_percent),
                'price_difference': anomaly.price_difference,
                'is_price_increase': anomaly.is_price_increase,
                'status': anomaly.status,
                'detected_at': anomaly.detected_at.isoformat(),
                'reviewed_at': anomaly.reviewed_at.isoformat() if anomaly.reviewed_at else None,
                'notes': anomaly.notes,
            }
            for anomaly in page
        ]
        
        return JsonResponse({
            'success': True,
            'data': anomalies,
            'pagination': {
                'page': page.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page.has_next(),
                'has_previous': page.has_previous(),
            }
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid parameter: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.error(f"Error listing anomalies: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@require_http_methods(["GET"])
def get_price_anomaly(request, anomaly_id):
    """
    Get a single price anomaly by ID
    """
    try:
        anomaly = PriceAnomaly.objects.get(id=anomaly_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': anomaly.id,
                'vendor': anomaly.vendor,
                'product_name': anomaly.product_name,
                'product_url': anomaly.product_url,
                'unit': anomaly.unit,
                'location': anomaly.location,
                'old_price': anomaly.old_price,
                'new_price': anomaly.new_price,
                'change_percent': float(anomaly.change_percent),
                'price_difference': anomaly.price_difference,
                'is_price_increase': anomaly.is_price_increase,
                'status': anomaly.status,
                'detected_at': anomaly.detected_at.isoformat(),
                'reviewed_at': anomaly.reviewed_at.isoformat() if anomaly.reviewed_at else None,
                'notes': anomaly.notes,
            }
        })
        
    except PriceAnomaly.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Anomaly not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting anomaly {anomaly_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)



@require_http_methods(["POST"])
def review_price_anomaly(request, anomaly_id):
    """
    Review a price anomaly (approve/reject)
    
    Body parameters:
    - status: New status (reviewed, approved, rejected)
    - notes: Optional review notes
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        status = data.get('status', 'reviewed')
        notes = data.get('notes', '')
        
        # Validate status
        valid_statuses = ['reviewed', 'approved', 'rejected']
        if status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, status=400)
        
        # Update anomaly
        success = PriceAnomalyService.mark_as_reviewed(anomaly_id, status, notes)
        
        if success:
            anomaly = PriceAnomaly.objects.get(id=anomaly_id)
            return JsonResponse({
                'success': True,
                'message': f'Anomaly marked as {status}',
                'data': {
                    'id': anomaly.id,
                    'status': anomaly.status,
                    'reviewed_at': anomaly.reviewed_at.isoformat() if anomaly.reviewed_at else None,
                    'notes': anomaly.notes,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Anomaly not found'
            }, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error reviewing anomaly {anomaly_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@require_http_methods(["GET"])
def get_anomaly_statistics(request):
    """
    Get statistics about price anomalies
    
    Returns counts by status and vendor
    """
    try:
        # Get counts by status
        status_counts = {}
        for status_code, status_name in PriceAnomaly.STATUS_CHOICES:
            status_counts[status_code] = PriceAnomaly.objects.filter(status=status_code).count()
        
        # Get counts by vendor
        vendor_counts = {}
        for vendor_code, vendor_name in PriceAnomaly.VENDOR_CHOICES:
            vendor_counts[vendor_code] = PriceAnomaly.objects.filter(vendor=vendor_code).count()
        
        # Get total count
        total_count = PriceAnomaly.objects.count()
        
        # Get pending count
        pending_count = PriceAnomaly.objects.filter(status='pending').count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'total_count': total_count,
                'pending_count': pending_count,
                'by_status': status_counts,
                'by_vendor': vendor_counts,
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting anomaly statistics: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

