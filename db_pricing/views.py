from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from db_pricing.utils import check_database_connection, check_gemilang_table_exists


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

