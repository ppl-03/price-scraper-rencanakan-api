from typing import List, Optional, Dict, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from db_pricing.models import DepoBangunanProduct
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProductData:
    
    name: str
    price: int
    url: str
    unit: str = ''
    
    def validate(self) -> None:
        
        if not self.name or not self.name.strip():
            raise ValidationError("Product name cannot be empty")
        
        if self.price < 0:
            raise ValidationError("Product price cannot be negative")
        
        if not self.url or not self.url.strip():
            raise ValidationError("Product URL cannot be empty")
        
        if len(self.name) > 500:
            raise ValidationError("Product name exceeds maximum length of 500 characters")
        
        if len(self.url) > 1000:
            raise ValidationError("Product URL exceeds maximum length of 1000 characters")
        
        if len(self.unit) > 50:
            raise ValidationError("Product unit exceeds maximum length of 50 characters")

class IProductRepository:
    
    def create(self, product_data: ProductData) -> DepoBangunanProduct:
        
        raise NotImplementedError
    
    def get_by_id(self, product_id: int) -> Optional[DepoBangunanProduct]:
        
        raise NotImplementedError
    
    def update(self, product_id: int, product_data: ProductData) -> DepoBangunanProduct:
        
        raise NotImplementedError
    
    def delete(self, product_id: int) -> bool:
        
        raise NotImplementedError
    
    def get_all(self) -> List[DepoBangunanProduct]:
        
        raise NotImplementedError

class DepoBangunanProductRepository(IProductRepository):
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create(self, product_data: ProductData) -> DepoBangunanProduct:
        
        try:
            product_data.validate()
            
            product = DepoBangunanProduct.objects.create(
                name=product_data.name.strip(),
                price=product_data.price,
                url=product_data.url.strip(),
                unit=product_data.unit.strip()
            )
            
            self.logger.info(f"Created product: {product.id} - {product.name}")
            return product
            
        except ValidationError as e:
            self.logger.error(f"Validation error creating product: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating product: {e}")
            raise
    
    def get_by_id(self, product_id: int) -> Optional[DepoBangunanProduct]:
        
        try:
            return DepoBangunanProduct.objects.get(id=product_id)
        except DepoBangunanProduct.DoesNotExist:
            self.logger.warning(f"Product not found: {product_id}")
            return None
    
    def update(self, product_id: int, product_data: ProductData) -> DepoBangunanProduct:
        
        product_data.validate()
        
        product = DepoBangunanProduct.objects.get(id=product_id)
        product.name = product_data.name.strip()
        product.price = product_data.price
        product.url = product_data.url.strip()
        product.unit = product_data.unit.strip()
        product.save()
        
        self.logger.info(f"Updated product: {product.id} - {product.name}")
        return product
    
    def delete(self, product_id: int) -> bool:
        
        try:
            product = DepoBangunanProduct.objects.get(id=product_id)
            product.delete()
            self.logger.info(f"Deleted product: {product_id}")
            return True
        except DepoBangunanProduct.DoesNotExist:
            self.logger.warning(f"Product not found for deletion: {product_id}")
            return False
    
    def get_all(self) -> List[DepoBangunanProduct]:
        
        return list(DepoBangunanProduct.objects.all())

class ProductQueryService:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def filter_by_name(self, keyword: str) -> List[DepoBangunanProduct]:
        
        if not keyword or not keyword.strip():
            return []
        
        return list(
            DepoBangunanProduct.objects.filter(name__icontains=keyword.strip())
        )
    
    def filter_by_price_range(
        self, 
        min_price: Optional[int] = None, 
        max_price: Optional[int] = None
    ) -> List[DepoBangunanProduct]:
        
        queryset = DepoBangunanProduct.objects.all()
        
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        
        return list(queryset)
    
    def filter_by_unit(self, unit: str) -> List[DepoBangunanProduct]:
        
        return list(DepoBangunanProduct.objects.filter(unit=unit))
    
    def get_recent_products(self, limit: int = 10) -> List[DepoBangunanProduct]:
        
        return list(
            DepoBangunanProduct.objects.order_by('-created_at')[:limit]
        )
    
    def search_products(
        self,
        keyword: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        unit: Optional[str] = None
    ) -> List[DepoBangunanProduct]:
        
        queryset = DepoBangunanProduct.objects.all()
        
        if keyword and keyword.strip():
            queryset = queryset.filter(name__icontains=keyword.strip())
        
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        
        if unit:
            queryset = queryset.filter(unit=unit)
        
        return list(queryset)

class BulkProductService:
    
    def __init__(self, repository: IProductRepository):
        self.repository = repository
        self.logger = logging.getLogger(__name__)
    
    @transaction.atomic
    def bulk_create(self, products_data: List[ProductData]) -> List[DepoBangunanProduct]:
        
        # Validate all products first
        for product_data in products_data:
            product_data.validate()
        
        # Create all products
        products = [
            DepoBangunanProduct(
                name=pd.name.strip(),
                price=pd.price,
                url=pd.url.strip(),
                unit=pd.unit.strip()
            )
            for pd in products_data
        ]
        
        created = DepoBangunanProduct.objects.bulk_create(products)
        self.logger.info(f"Bulk created {len(created)} products")
        
        return created
    
    @transaction.atomic
    def bulk_update_prices(
        self, 
        product_ids: List[int], 
        new_price: int
    ) -> int:
        
        if new_price < 0:
            raise ValidationError("Price cannot be negative")
        
        updated_count = DepoBangunanProduct.objects.filter(
            id__in=product_ids
        ).update(price=new_price)
        
        self.logger.info(f"Bulk updated {updated_count} products with new price: {new_price}")
        return updated_count
    
    @transaction.atomic
    def bulk_delete(self, product_ids: List[int]) -> int:
        
        deleted_count, _ = DepoBangunanProduct.objects.filter(
            id__in=product_ids
        ).delete()
        
        self.logger.info(f"Bulk deleted {deleted_count} products")
        return deleted_count

class DatabaseHandshakeService:
    
    def __init__(
        self,
        repository: Optional[IProductRepository] = None,
        query_service: Optional[ProductQueryService] = None
    ):
        self.repository = repository or DepoBangunanProductRepository()
        self.query_service = query_service or ProductQueryService()
        self.bulk_service = BulkProductService(self.repository)
        self.logger = logging.getLogger(__name__)
    
    def create_product(
        self,
        name: str,
        price: int,
        url: str,
        unit: str = ''
    ) -> DepoBangunanProduct:
        
        product_data = ProductData(name=name, price=price, url=url, unit=unit)
        return self.repository.create(product_data)
    
    def get_product(self, product_id: int) -> Optional[DepoBangunanProduct]:
        
        return self.repository.get_by_id(product_id)
    
    def update_product(
        self,
        product_id: int,
        name: str,
        price: int,
        url: str,
        unit: str = ''
    ) -> DepoBangunanProduct:
        
        product_data = ProductData(name=name, price=price, url=url, unit=unit)
        return self.repository.update(product_id, product_data)
    
    def delete_product(self, product_id: int) -> bool:
        
        return self.repository.delete(product_id)
    
    def search_by_keyword(self, keyword: str) -> List[DepoBangunanProduct]:
        
        return self.query_service.filter_by_name(keyword)
    
    def get_all_products(self) -> List[DepoBangunanProduct]:
        
        return self.repository.get_all()
    
    def verify_connection(self) -> Dict[str, Any]:
        
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    self.logger.info("Database connection verified successfully")
                    return {
                        'status': 'success',
                        'connected': True,
                        'message': 'Database connection is healthy'
                    }
        except Exception as e:
            self.logger.error(f"Database connection verification failed: {e}")
            return {
                'status': 'error',
                'connected': False,
                'message': f'Database connection failed: {str(e)}'
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        
        try:
            total_products = DepoBangunanProduct.objects.count()
            
            if total_products == 0:
                return {
                    'total_products': 0,
                    'avg_price': 0,
                    'min_price': 0,
                    'max_price': 0
                }
            
            from django.db.models import Avg, Min, Max
            
            stats = DepoBangunanProduct.objects.aggregate(
                avg_price=Avg('price'),
                min_price=Min('price'),
                max_price=Max('price')
            )
            
            return {
                'total_products': total_products,
                'avg_price': float(stats['avg_price']) if stats['avg_price'] else 0,
                'min_price': stats['min_price'] or 0,
                'max_price': stats['max_price'] or 0
            }
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {
                'total_products': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'error': str(e)
            }
    
    def show_all_tables(self) -> Dict[str, Any]:
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                table_list = [table[0] for table in tables]
                
                self.logger.info(f"Found {len(table_list)} tables in database")
                return {
                    'status': 'success',
                    'total_tables': len(table_list),
                    'tables': table_list,
                    'database': connection.settings_dict.get('NAME', 'unknown')
                }
        except Exception as e:
            self.logger.error(f"Error retrieving tables: {e}")
            return {
                'status': 'error',
                'total_tables': 0,
                'tables': [],
                'error': str(e)
            }
    
    def check_table_exists(self, table_name: str) -> Dict[str, Any]:
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE %s", [table_name])
                result = cursor.fetchone()
                
                exists = result is not None
                
                if exists:
                    self.logger.info(f"Table '{table_name}' exists")
                else:
                    self.logger.warning(f"Table '{table_name}' does not exist")
                
                return {
                    'status': 'success',
                    'table_name': table_name,
                    'exists': exists,
                    'database': connection.settings_dict.get('NAME', 'unknown')
                }
        except Exception as e:
            self.logger.error(f"Error checking table existence: {e}")
            return {
                'status': 'error',
                'table_name': table_name,
                'exists': False,
                'error': str(e)
            }
