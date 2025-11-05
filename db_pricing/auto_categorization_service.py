from db_pricing.models import GemilangProduct, Mitra10Product, DepoBangunanProduct, JuraganMaterialProduct
from db_pricing.categorization import ProductCategorizer


class AutoCategorizationService:
    
    MODEL_MAP = {
        'gemilang': GemilangProduct,
        'mitra10': Mitra10Product,
        'depobangunan': DepoBangunanProduct,
        'juragan_material': JuraganMaterialProduct,
    }
    
    def __init__(self):
        self.categorizer = ProductCategorizer()
    
    def categorize_products(self, vendor: str, product_ids: list[int]) -> dict:
        model_class = self.MODEL_MAP.get(vendor)
        if not model_class:
            raise ValueError(f"Unknown vendor: {vendor}")
        
        products = model_class.objects.filter(id__in=product_ids)
        
        categorized_count = 0
        for product in products:
            category = self.categorizer.categorize(product.name)
            if category:
                product.category = category
                product.save(update_fields=['category'])
                categorized_count += 1
        
        return {
            'total': len(product_ids),
            'categorized': categorized_count,
            'uncategorized': len(product_ids) - categorized_count
        }
    
    def categorize_all_products(self, vendor: str) -> dict:
        model_class = self.MODEL_MAP.get(vendor)
        if not model_class:
            raise ValueError(f"Unknown vendor: {vendor}")
        
        products = model_class.objects.all()
        
        categorized_count = 0
        for product in products:
            category = self.categorizer.categorize(product.name)
            if category:
                product.category = category
                product.save(update_fields=['category'])
                categorized_count += 1
        
        total = products.count()
        return {
            'total': total,
            'categorized': categorized_count,
            'uncategorized': total - categorized_count
        }