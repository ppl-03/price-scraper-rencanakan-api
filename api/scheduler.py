from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterable, List, Optional
from importlib import import_module
from django.utils import timezone
from datetime import datetime

def _now():
    try:
        return timezone.now()
    except Exception:
        return datetime.now()

from .views import get_scraper_factory

logger = logging.getLogger(__name__)


class BaseScheduler:
    def get_categories(self, vendor: str, server_time) -> List[str]:
        try:
            mod = import_module(f"api.{vendor}.categorizer")
            fn = getattr(mod, 'get_categories', None)
            if fn:
                try:
                    return list(fn(server_time))
                except TypeError:
                    return list(fn())
        except Exception:
            pass
        return []

    def create_scraper(self, vendor: str):
        return get_scraper_factory(vendor)

    def load_db_service(self, vendor: str):
        try:
            mod = import_module(f"api.{vendor}.database_service")
        except Exception:
            return None
        for attr in dir(mod):
            if 'DatabaseService' in attr:
                cls = getattr(mod, attr)
                try:
                    return cls()
                except Exception:
                    return None
        return None

    def normalize_products(self, products: List[Any]) -> List[Dict[str, Any]]:
        out = []
        logger.info(f"Normalizing {len(products)} products")
        
        for idx, p in enumerate(products):
            try:
                if isinstance(p, dict):
                    # Create clean copy
                    normalized = {
                        'name': str(p.get('name', '')).strip(),
                        'price': int(p.get('price', 0)),
                        'url': str(p.get('url', '')).strip(),
                        'unit': str(p.get('unit') or '').strip(),  # ✅ Convert None to ''
                        'location': str(p.get('location') or '').strip(),
                        'category': str(p.get('category') or '').strip(),
                    }
                else:
                    # Extract from object
                    normalized = {
                        'name': str(getattr(p, 'name', '')).strip(),
                        'price': int(getattr(p, 'price', 0)),
                        'url': str(getattr(p, 'url', '')).strip(),
                        'unit': str(getattr(p, 'unit', None) or '').strip(),  # ✅ Handle None
                        'location': str(getattr(p, 'location', None) or '').strip(),
                        'category': str(getattr(p, 'category', None) or '').strip(),
                    }
                
                # Validate required fields
                if not normalized['name'] or not normalized['url']:
                    logger.warning(f"Product #{idx} missing name or url, skipping")
                    continue
                
                if normalized['price'] <= 0:
                    logger.warning(f"Product #{idx} has invalid price: {normalized['price']}, skipping")
                    continue
                
                out.append(normalized)
                
            except Exception as e:
                logger.warning(f"Unable to normalize product #{idx}: {p} - {e}")
        
        logger.info(f"Successfully normalized {len(out)}/{len(products)} products")
        return out
    
    def _get_product_url(self, product):
        """Extract URL from product (dict or object)."""
        return product.get('url') if isinstance(product, dict) else getattr(product, 'url', None)
    
    def _set_product_unit(self, product, unit):
        """Set unit on product (dict or object)."""
        if isinstance(product, dict):
            product['unit'] = unit
        else:
            try:
                setattr(product, 'unit', unit)
            except Exception:
                pass
    
    def enrich_unit(self, scraper, product):
        try:
            if not hasattr(scraper, 'scrape_product_details'):
                return
            
            url = self._get_product_url(product)
            if not url:
                return
            
            detail = scraper.scrape_product_details(url)
            unit = getattr(detail, 'unit', None)
            if unit:
                self._set_product_unit(product, unit)
        except Exception:
            pass

    def _calculate_timing_delay(self, server_time, expected_start_time):
        """Calculate timing delay if expected start time is provided."""
        if not expected_start_time:
            return None
        try:
            if hasattr(server_time, 'timestamp'):
                return server_time.timestamp() - expected_start_time.timestamp()
            return 0
        except Exception:
            return None
    
    def _initialize_summary(self, server_time, start_timestamp, timing_delay, vendors):
        """Initialize the summary dictionary."""
        return {
            'server_time': str(server_time),
            'start_timestamp': start_timestamp,
            'timing_delay_seconds': timing_delay,
            'vendors': {},
            'errors': [],
            'total_vendors': len(vendors),
            'successful_vendors': 0,
            'failed_vendors': 0
        }
    
    def _initialize_vendor_result(self):
        """Initialize vendor result dictionary."""
        return {
            'keywords': 0,
            'products_found': 0,
            'saved': 0,
            'errors': [],
            'status': 'unknown',
            'duration_seconds': 0,
            'scrape_failures': 0,
            'scrape_attempts': 0
        }
    
    def _handle_no_categories(self, vendor, vendor_result, summary):
        """Handle case when vendor has no categories."""
        vendor_result['status'] = 'skipped_no_categories'
        vendor_result['errors'].append(f'No categories returned for vendor {vendor}')
        logger.warning(f'Vendor {vendor} skipped: no categories available')
        summary['vendors'][vendor] = vendor_result
        summary['failed_vendors'] += 1
    
    def _handle_scraper_creation_error(self, vendor, e, vendor_result, summary):
        """Handle scraper creation failure."""
        vendor_result['status'] = 'failed_scraper_creation'
        error_msg = f'Failed to create scraper for {vendor}: {type(e).__name__}: {str(e)}'
        vendor_result['errors'].append(error_msg)
        logger.error(error_msg)
        summary['errors'].append({'vendor': vendor, 'error': error_msg, 'type': 'scraper_creation'})
        summary['vendors'][vendor] = vendor_result
        summary['failed_vendors'] += 1
    
    def _enrich_products_with_units(self, scraper, products):
        """Enrich products with unit information if missing."""
        for prod in products:
            prod_unit = prod.get('unit') if isinstance(prod, dict) else getattr(prod, 'unit', None)
            if not prod_unit:
                self.enrich_unit(scraper, prod)
    
    def _extract_saved_count_from_price_update(self, res):
        """Extract saved count from price update response."""
        if not isinstance(res, dict):
            return 0
        saved_count = int(res.get('inserted', 0) or 0)
        return saved_count or int(res.get('new_count', 0) or 0)
    
    def _extract_saved_count_from_regular_save(self, res, products_data):
        """Extract saved count from regular save response."""
        if isinstance(res, tuple):
            return len(products_data) if res[0] else 0
        elif isinstance(res, bool):
            return len(products_data) if res else 0
        elif isinstance(res, dict):
            return int(res.get('inserted', 0) or res.get('new_count', 0) or res.get('saved', 0) or 0)
        return 0
    
    def _save_products(self, db_service, products_data, use_price_update, vendor, keyword, vendor_result):
        """Save products to database and return count saved."""
        # print("Products Data to Save:", products_data)
        try:
            if use_price_update and hasattr(db_service, 'save_with_price_update'):
                res = db_service.save_with_price_update(products_data)
                return self._extract_saved_count_from_price_update(res)
            else:
                res = db_service.save(products_data)
                return self._extract_saved_count_from_regular_save(res, products_data)
        except Exception as e:
            error_msg = f'{vendor} database save failed for keyword "{keyword}": {type(e).__name__}: {str(e)}'
            vendor_result['errors'].append(error_msg)
            logger.error(error_msg)
            return 0
    
    def _process_scrape_result(self, scraper, result, vendor, keyword, page, vendor_result, db_service, use_price_update, max_products_per_keyword):
        """Process a single scrape result and return products found and saved counts."""
        if not getattr(result, 'success', False):
            vendor_result['scrape_failures'] += 1
            error_msg = f'{vendor} scrape failed for keyword "{keyword}" page {page}: {getattr(result, "error_message", "unknown error")}'
            vendor_result['errors'].append(error_msg)
            logger.error(error_msg)
            return 0, 0
        
        products = list(getattr(result, 'products', []) or [])
        self._enrich_products_with_units(scraper, products)
        
        products_data = self.normalize_products(products)
        products_found = len(products_data)
        
        if max_products_per_keyword is not None and len(products_data) > max_products_per_keyword:
            products_data = products_data[:max_products_per_keyword]
        
        saved_count = 0
        if db_service and products_data:
            saved_count = self._save_products(db_service, products_data, use_price_update, vendor, keyword, vendor_result)
        
        return products_found, saved_count
    
    def _scrape_vendor_keywords(self, vendor, scraper, pages_per_keyword, vendor_result, db_service, use_price_update, max_products_per_keyword,keyword=None):
        """Scrape all keywords for a vendor and return total products found and saved."""
        total_products = 0
        total_saved = 0
        
        # for keyword in cats:
        for page in range(pages_per_keyword):
            vendor_result['scrape_attempts'] += 1
            try:
                result = scraper.scrape_products(keyword=keyword, sort_by_price=True, page=page)
                found, saved = self._process_scrape_result(
                    scraper, result, vendor, keyword, page, vendor_result,
                    db_service, use_price_update, max_products_per_keyword
                )
                total_products += found
                total_saved += saved
            except Exception as e:
                vendor_result['scrape_failures'] += 1
                error_msg = f'{vendor} exception during scrape keyword "{keyword}" page {page}: {type(e).__name__}: {str(e)}'
                vendor_result['errors'].append(error_msg)
                logger.exception(error_msg)
        
        return total_products, total_saved
    
    def _determine_vendor_status(self, vendor_result, total_products, summary, vendor):
        """Determine final status of vendor scraping operation."""
        if vendor_result['scrape_failures'] == vendor_result['scrape_attempts'] and vendor_result['scrape_attempts'] > 0:
            vendor_result['status'] = 'failed_all_scrapes'
            summary['failed_vendors'] += 1
            summary['errors'].append({
                'vendor': vendor,
                'error': f'All {vendor_result["scrape_attempts"]} scrape attempts failed',
                'type': 'complete_failure'
            })
        elif vendor_result['scrape_failures'] > 0:
            vendor_result['status'] = 'partial_success'
            summary['successful_vendors'] += 1
        elif total_products == 0:
            vendor_result['status'] = 'no_products_found'
            vendor_result['errors'].append(f'No products found for vendor {vendor}')
            summary['successful_vendors'] += 1
        else:
            vendor_result['status'] = 'success'
            summary['successful_vendors'] += 1
    
    def _process_single_vendor(self, vendor, server_time, summary,use_price_update, max_products_per_keyword, search_keyword=None):
        """Process scraping for a single vendor."""
        vendor_start = time.time()
        vendor_result = self._initialize_vendor_result()
        
        try:
            # cats = self.get_categories(vendor, server_time)
            # if not cats:
            #     self._handle_no_categories(vendor, vendor_result, summary)
            #     return
            
            # vendor_result['keywords'] = len(cats)
            pages_per_keyword = 1  # Could be parameterized if needed
            
            
            try:
                scraper = self.create_scraper(vendor)
            except Exception as e:
                self._handle_scraper_creation_error(vendor, e, vendor_result, summary)
                return
            
            db_service = self.load_db_service(vendor)
            if not db_service:
                logger.warning(f'No database service available for vendor {vendor}')
            
            total_products, total_saved = self._scrape_vendor_keywords(
                vendor, scraper, pages_per_keyword, vendor_result,
                db_service, use_price_update, max_products_per_keyword, keyword=search_keyword
            )
            
            vendor_result['products_found'] = total_products
            vendor_result['saved'] = total_saved
            
            self._determine_vendor_status(vendor_result, total_products, summary, vendor)
                
        except Exception as e:
            vendor_result['status'] = 'failed_exception'
            error_msg = f'{vendor} critical exception: {type(e).__name__}: {str(e)}'
            vendor_result['errors'].append(error_msg)
            logger.exception(error_msg)
            summary['errors'].append({'vendor': vendor, 'error': error_msg, 'type': 'critical_exception'})
            summary['failed_vendors'] += 1
        
        vendor_result['duration_seconds'] = round(time.time() - vendor_start, 2)
        summary['vendors'][vendor] = vendor_result

    def run(self, server_time=None, vendors: Optional[Iterable[str]] = None, use_price_update: bool = False, max_products_per_keyword: Optional[int] = None, expected_start_time=None, search_keyword=None) -> Dict[str, Any]:
        start_timestamp = time.time()
        server_time = server_time or _now()
        
        timing_delay = self._calculate_timing_delay(server_time, expected_start_time)
        
        default_vendors = ['depobangunan', 'gemilang', 'juragan_material', 'mitra10']
        vendors = list(vendors) if vendors is not None else default_vendors
        
        summary = self._initialize_summary(server_time, start_timestamp, timing_delay, vendors)
        
        for vendor in vendors:
            self._process_single_vendor(
                vendor=vendor, server_time=server_time, summary=summary,
                use_price_update=use_price_update, 
                max_products_per_keyword=max_products_per_keyword,
                search_keyword=search_keyword
            )
            
        summary['total_duration_seconds'] = round(time.time() - start_timestamp, 2)
        summary['end_timestamp'] = time.time()
        
        return summary

