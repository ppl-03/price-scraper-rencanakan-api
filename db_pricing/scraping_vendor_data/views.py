from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
import json

from .services import DjangoScrapingVendorDataRepository, ScrapingVendorDataService, RequiredFieldsValidator, FieldLengthValidator


@method_decorator(csrf_exempt, name='dispatch')
class ScrapingVendorDataView(View):
    """API view for scraping vendor data operations."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        repository = DjangoScrapingVendorDataRepository()
        validators = [RequiredFieldsValidator(), FieldLengthValidator()]
        self.service = ScrapingVendorDataService(repository, validators)
    
    def get(self, request, vendor_data_id=None):
        """GET /scraping-vendor-data/ or GET /scraping-vendor-data/{id}/"""
        try:
            # Ensure table exists
            self.service.ensure_table_exists()
            
            if vendor_data_id:
                # Get specific record
                vendor_data = self.service.get_vendor_data_by_id(vendor_data_id)
                if not vendor_data:
                    return JsonResponse({'error': 'Vendor data not found'}, status=404)
                
                return JsonResponse({
                    'id': vendor_data.id,
                    'product_name': vendor_data.product_name,
                    'price': vendor_data.price,
                    'unit': vendor_data.unit,
                    'vendor': vendor_data.vendor,
                    'location': vendor_data.location,
                    'created_at': vendor_data.created_at.isoformat(),
                    'updated_at': vendor_data.updated_at.isoformat(),
                })
            else:
                # Get all records or filter
                vendor = request.GET.get('vendor')
                location = request.GET.get('location')
                
                if vendor:
                    vendor_data_list = self.service.get_vendor_data_by_vendor(vendor)
                elif location:
                    vendor_data_list = self.service.get_vendor_data_by_location(location)
                else:
                    vendor_data_list = self.service.get_all_vendor_data()
                
                data = []
                for vendor_data in vendor_data_list:
                    data.append({
                        'id': vendor_data.id,
                        'product_name': vendor_data.product_name,
                        'price': vendor_data.price,
                        'unit': vendor_data.unit,
                        'vendor': vendor_data.vendor,
                        'location': vendor_data.location,
                        'created_at': vendor_data.created_at.isoformat(),
                        'updated_at': vendor_data.updated_at.isoformat(),
                    })
                
                return JsonResponse({'data': data})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def post(self, request):
        """POST /scraping-vendor-data/"""
        try:
            # Ensure table exists
            self.service.ensure_table_exists()
            
            data = json.loads(request.body)
            
            # Extract required fields
            product_name = data.get('product_name')
            price = data.get('price')
            unit = data.get('unit')
            vendor = data.get('vendor')
            location = data.get('location')
            
            # Create vendor data
            vendor_data = self.service.create_vendor_data(
                product_name=product_name,
                price=price,
                unit=unit,
                vendor=vendor,
                location=location
            )
            
            return JsonResponse({
                'id': vendor_data.id,
                'product_name': vendor_data.product_name,
                'price': vendor_data.price,
                'unit': vendor_data.unit,
                'vendor': vendor_data.vendor,
                'location': vendor_data.location,
                'created_at': vendor_data.created_at.isoformat(),
                'updated_at': vendor_data.updated_at.isoformat(),
            }, status=201)
        
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def put(self, request, vendor_data_id):
        """PUT /scraping-vendor-data/{id}/"""
        try:
            # Ensure table exists
            self.service.ensure_table_exists()
            
            data = json.loads(request.body)
            
            # Update vendor data
            vendor_data = self.service.update_vendor_data(vendor_data_id, **data)
            
            if not vendor_data:
                return JsonResponse({'error': 'Vendor data not found'}, status=404)
            
            return JsonResponse({
                'id': vendor_data.id,
                'product_name': vendor_data.product_name,
                'price': vendor_data.price,
                'unit': vendor_data.unit,
                'vendor': vendor_data.vendor,
                'location': vendor_data.location,
                'created_at': vendor_data.created_at.isoformat(),
                'updated_at': vendor_data.updated_at.isoformat(),
            })
        
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def delete(self, request, vendor_data_id):
        """DELETE /scraping-vendor-data/{id}/"""
        try:
            # Ensure table exists
            self.service.ensure_table_exists()
            
            success = self.service.delete_vendor_data(vendor_data_id)
            
            if not success:
                return JsonResponse({'error': 'Vendor data not found'}, status=404)
            
            return JsonResponse({'message': 'Vendor data deleted successfully'})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)