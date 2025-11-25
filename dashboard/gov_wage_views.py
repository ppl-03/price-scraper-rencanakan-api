from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_GET
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.db.models import Q
import json
import logging
import re
import time

from api.government_wage.scraper import (
    get_cached_or_scrape, 
    GovernmentWageItem,
    scrape_and_cache
)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_REGION = 'Kab. Cilacap'
DEFAULT_PROVINCE = 'Jawa Tengah'
DEFAULT_YEAR = '2025'


@require_GET
def test_api(request):
    """Test endpoint to verify API is working"""
    try:
        from api.government_wage.scraper import load_from_local_file
        
        # Try to load Cilacap data
        items = load_from_local_file(DEFAULT_REGION, DEFAULT_YEAR)
        
        if items:
            return JsonResponse({
                'success': True,
                'message': 'Cache file loaded successfully',
                'item_count': len(items),
                'first_item': {
                    'item_number': items[0].item_number,
                    'work_code': items[0].work_code,
                    'work_description': items[0].work_description,
                } if items else None
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No cached data found',
                'region': DEFAULT_REGION,
                'year': DEFAULT_YEAR
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        })


@require_GET
def gov_wage_page(request):
    context = {
        'page_title': 'HSPK Upah Pemerintah',
        'default_region': DEFAULT_REGION,
        'available_regions': [
            {'value': DEFAULT_REGION, 'name': 'Kabupaten Cilacap'},
            {'value': 'Kab. Banyumas', 'name': 'Kabupaten Banyumas'},
            {'value': 'Kab. Purbalingga', 'name': 'Kabupaten Purbalingga'},
            {'value': 'Kab. Banjarnegara', 'name': 'Kabupaten Banjarnegara'},
            {'value': 'Kab. Kebumen', 'name': 'Kabupaten Kebumen'},
            {'value': 'Kab. Purworejo', 'name': 'Kabupaten Purworejo'},
            {'value': 'Kab. Wonosobo', 'name': 'Kabupaten Wonosobo'},
            {'value': 'Kab. Magelang', 'name': 'Kabupaten Magelang'},
        ],
        'categories': [
            {'value': 'pondasi', 'name': 'Pondasi'},
            {'value': 'bekisting', 'name': 'Bekisting'},
            {'value': 'batu', 'name': 'Batu & Mortar'},
            {'value': 'plat', 'name': 'Plat & Lantai'},
            {'value': 'dinding', 'name': 'Dinding'},
        ]
    }
    return render(request, 'dashboard/gov_wage_page.html', context)


@require_http_methods(["GET"])
def get_wage_data(request):
    """
    Get government wage data with pagination (2025 version with JSON caching)
    """
    try:
        # Get query parameters
        region = request.GET.get('region', DEFAULT_REGION)
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        year = request.GET.get('year', DEFAULT_YEAR)
        force_refresh = request.GET.get('force_refresh', 'false').lower() == 'true'
        # Check if client wants all data for client-side filtering
        get_all = request.GET.get('all', 'false').lower() == 'true'
        
        logger.info(f"Getting wage data for region: {region}, page: {page}, year: {year}, get_all: {get_all}")
        
        # Get data from cache or scrape using 2025 JSON caching logic
        start_time = time.time()
        
        try:
            items = get_cached_or_scrape(region, year, force_refresh)
            logger.info(f"Successfully retrieved {len(items)} items from cache/scraper")
        except Exception as scraper_error:
            logger.error(f"Error getting cached data: {str(scraper_error)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Terjadi kesalahan saat mengambil data: {str(scraper_error)}'
            }, status=500)
        
        data_load_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        logger.info(f"Loaded {len(items)} items (load time: {data_load_time:.2f}ms)")
        
        # Convert to the format expected by frontend
        all_data = []
        for item in items:
            try:
                all_data.append({
                    'item_number': item.item_number,
                    'work_code': item.work_code,
                    'work_description': item.work_description,
                    'unit': item.unit,
                    'unit_price_idr': item.unit_price_idr,
                    'region': item.region,
                    'edition': item.edition,
                    'year': item.year,
                    'sector': item.sector,
                    'category': categorize_work_item(item.work_description)
                })
            except Exception as item_error:
                logger.error(f"Error processing item: {str(item_error)}")
                continue
        
        # If get_all is true, return all data without pagination
        if get_all:
            logger.info(f"Returning ALL {len(all_data)} items for client-side filtering")
            return JsonResponse({
                'success': True,
                'data': all_data,
                'pagination': {
                    'current_page': 1,
                    'total_pages': 1,
                    'total_items': len(all_data),
                    'per_page': len(all_data),
                    'has_next': False,
                    'has_previous': False,
                },
                'region': region,
                'year': year,
                'data_load_time_ms': round(data_load_time, 2),
                'cached': data_load_time < 100
            })
        
        # Calculate pagination for paginated requests
        total_items = len(all_data)
        total_pages = (total_items + per_page - 1) // per_page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        page_data = all_data[start_index:end_index]
        
        logger.info(f"Returning {len(page_data)} items for page {page}")
        
        return JsonResponse({
            'success': True,
            'data': page_data,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_items': total_items,
                'per_page': per_page,
                'has_next': page < total_pages,
                'has_previous': page > 1,
            },
            'region': region,
            'year': year,
            'data_load_time_ms': round(data_load_time, 2),
            'cached': data_load_time < 100  # If load time is very fast, it was cached
        })
        
    except Exception as e:
        logger.error(f"Error in get_wage_data: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Terjadi kesalahan saat mengambil data HSPK: {str(e)}'
        }, status=500)


def get_page_data_filtered(region, search_query, category, price_range, page, per_page, sort_by, sort_order):
    try:
        year = DEFAULT_YEAR
        
        logger.info(f"FILTERED PAGINATION - Getting data for region: {region}")
        
        # use 2025 JSON caching system
        items = get_cached_or_scrape(region, year, force_refresh=False)
        logger.info(f"FILTERED PAGINATION - Got {len(items)} total items for region: {region}")
        
        wage_data = [
            {
                'item_number': item.item_number,
                'work_code': item.work_code,
                'work_description': item.work_description,
                'unit': item.unit,
                'unit_price_idr': item.unit_price_idr,
                'region': item.region,
                'edition': item.edition,
                'year': item.year,
                'sector': item.sector,
                'category': categorize_work_item(item.work_description)
            }
            for item in items
        ]
        
        filtered_data = apply_filters(wage_data, search_query, category, price_range)
        
        filtered_data = apply_sorting(filtered_data, sort_by, sort_order)
        
        paginator = Paginator(filtered_data, per_page)
        page_obj = paginator.get_page(page)
        
        response_data = {
            'success': True,
            'data': list(page_obj),
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'per_page': per_page,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
            'region': region,
            'year': year,
            'filters_applied': {
                'search': search_query,
                'category': category,
                'price_range': price_range,
            },
            'cached': True  
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in filtered pagination: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Terjadi kesalahan saat mengambil data dengan filter'
        }, status=500)


@require_http_methods(["GET"])
def get_pagination_info(request):
    try:
        region = request.GET.get('region', DEFAULT_REGION)
        year = request.GET.get('year', DEFAULT_YEAR)
        
        items = get_cached_or_scrape(region, year, force_refresh=False)
        total_items = len(items)
        total_pages = (total_items + 10 - 1) // 10 
        
        return JsonResponse({
            'success': True,
            'region': region,
            'year': year,
            'total_items': total_items,
            'total_pages': total_pages
        })
        
    except Exception as e:
        logger.error(f"Error getting pagination info: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Gagal mendapatkan informasi pagination'
        }, status=500)


@require_http_methods(["GET"])
def get_available_regions(request):
    try:
        regions = [
            {'value': DEFAULT_REGION, 'name': 'Kabupaten Cilacap', 'province': DEFAULT_PROVINCE},
            {'value': 'Kab. Banyumas', 'name': 'Kabupaten Banyumas', 'province': DEFAULT_PROVINCE},
            {'value': 'Kab. Purbalingga', 'name': 'Kabupaten Purbalingga', 'province': DEFAULT_PROVINCE},
            {'value': 'Kab. Banjarnegara', 'name': 'Kabupaten Banjarnegara', 'province': DEFAULT_PROVINCE},
            {'value': 'Kab. Kebumen', 'name': 'Kabupaten Kebumen', 'province': DEFAULT_PROVINCE},
            {'value': 'Kab. Purworejo', 'name': 'Kabupaten Purworejo', 'province': DEFAULT_PROVINCE},
            {'value': 'Kab. Wonosobo', 'name': 'Kabupaten Wonosobo', 'province': DEFAULT_PROVINCE},
            {'value': 'Kab. Magelang', 'name': 'Kabupaten Magelang', 'province': DEFAULT_PROVINCE},
            {'value': 'Kab. Boyolali', 'name': 'Kabupaten Boyolali', 'province': DEFAULT_PROVINCE},
            {'value': 'Kab. Klaten', 'name': 'Kabupaten Klaten', 'province': DEFAULT_PROVINCE},
        ]
        
        return JsonResponse({
            'success': True,
            'regions': regions
        })
        
    except Exception as e:
        logger.error(f"Error in get_available_regions: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Terjadi kesalahan saat mengambil daftar wilayah'
        }, status=500)


@require_http_methods(["POST"])
@csrf_protect
def search_work_code(request):
    try:
        data = json.loads(request.body)
        work_code = data.get('work_code', '').strip()
        region = data.get('region', DEFAULT_REGION)
        year = data.get('year', DEFAULT_YEAR)
        
        if not work_code:
            return JsonResponse({
                'success': False,
                'error': 'Kode pekerjaan tidak boleh kosong'
            }, status=400)
        
        items = get_cached_or_scrape(region, year, force_refresh=False)
        
        filtered_items = [
            item for item in items 
            if work_code.lower() in item.work_code.lower()
        ]
        
        wage_data = [
            {
                'item_number': item.item_number,
                'work_code': item.work_code,
                'work_description': item.work_description,
                'unit': item.unit,
                'unit_price_idr': item.unit_price_idr,
                'region': item.region,
                'edition': item.edition,
                'year': item.year,
                'sector': item.sector,
                'category': categorize_work_item(item.work_description)
            }
            for item in filtered_items
        ]
        
        if wage_data:
            return JsonResponse({
                'success': True,
                'data': wage_data,
                'count': len(wage_data),
                'search_term': work_code,
                'region': region
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Tidak dapat menemukan data untuk kode pekerjaan "{work_code}"'
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Format data tidak valid'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in search_work_code: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Terjadi kesalahan saat mencari data'
        }, status=500)


def categorize_work_item(work_description):
    if not work_description:
        return 'lainnya'
    
    description_lower = work_description.lower()
    
    categories = {
        'pondasi': ['pondasi', 'fondasi', 'pile', 'tiang pancang'],
        'bekisting': ['bekisting', 'formwork', 'cetakan'],
        'batu': ['batu', 'mortar', 'adukan', 'semen'],
        'plat': ['plat', 'lantai', 'slab', 'floor'],
        'dinding': ['dinding', 'wall', 'tembok', 'sheerwall'],
        'atap': ['atap', 'roof', 'genteng', 'asbes'],
        'beton': ['beton', 'concrete', 'cor'],
        'besi': ['besi', 'baja', 'steel', 'tulangan'],
        'cat': ['cat', 'painting', 'pengecatan'],
        'pipa': ['pipa', 'pipe', 'perpipaan', 'plumbing'],
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in description_lower:
                return category
    
    return 'lainnya'


def apply_filters(data, search_query, category, price_range):
    filtered_data = data.copy()
    
    if search_query:
        filtered_data = apply_search_filter(filtered_data, search_query)
    
    if category:
        filtered_data = apply_category_filter(filtered_data, category)
    
    if price_range:
        filtered_data = apply_price_range_filter(filtered_data, price_range)
    
    return filtered_data


def apply_search_filter(data, search_query):
    search_lower = search_query.lower()
    return [
        item for item in data
        if (search_lower in item.get('work_description', '').lower() or
            search_lower in item.get('work_code', '').lower())
    ]


def apply_category_filter(data, category):
    return [
        item for item in data
        if item.get('category', '') == category
    ]


def apply_price_range_filter(data, price_range):
    try:
        min_price, max_price = parse_price_range(price_range)
        return [
            item for item in data
            if min_price <= item.get('unit_price_idr', 0) <= max_price
        ]
    except (ValueError, IndexError):
        logger.warning(f"Invalid price range format: {price_range}")
        return data


def parse_price_range(price_range):
    if price_range == '0-500000':
        return 0, 500000
    elif price_range == '500000-1000000':
        return 500000, 1000000
    elif price_range == '1000000-2000000':
        return 1000000, 2000000
    elif price_range == '2000000-':
        return 2000000, float('inf')
    else:
        parts = price_range.split('-')
        min_price = int(parts[0]) if parts[0] else 0
        max_price = int(parts[1]) if len(parts) > 1 and parts[1] else float('inf')
        return min_price, max_price


def apply_sorting(data, sort_by, sort_order):
    reverse_order = sort_order.lower() == 'desc'
    
    sort_key_map = {
        'item_number': lambda x: int(x.get('item_number', 0)) if str(x.get('item_number', '')).isdigit() else 0,
        'work_code': lambda x: x.get('work_code', ''),
        'work_description': lambda x: x.get('work_description', ''),
        'unit': lambda x: x.get('unit', ''),
        'unit_price_idr': lambda x: x.get('unit_price_idr', 0),
    }
    
    sort_key = sort_key_map.get(sort_by, sort_key_map['item_number'])
    
    try:
        return sorted(data, key=sort_key, reverse=reverse_order)
    except (TypeError, ValueError):
        return data