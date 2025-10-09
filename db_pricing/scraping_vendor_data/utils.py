"""
Utility functions and examples for using the Scraping Vendor Data feature.

This module demonstrates how to use the scraping vendor data functionality,
including creating, reading, updating, and deleting vendor data records.
"""

from typing import List, Optional
from scraping_vendor_data.models import ScrapingVendorData
from scraping_vendor_data.services import (
    DjangoScrapingVendorDataRepository, 
    ScrapingVendorDataService, 
    RequiredFieldsValidator, 
    FieldLengthValidator
)


def setup_scraping_service() -> ScrapingVendorDataService:
    """
    Set up and return a configured ScrapingVendorDataService instance.
    
    Returns:
        ScrapingVendorDataService: Configured service instance
    """
    repository = DjangoScrapingVendorDataRepository()
    validators = [RequiredFieldsValidator(), FieldLengthValidator()]
    return ScrapingVendorDataService(repository, validators)


def create_sample_vendor_data() -> List[ScrapingVendorData]:
    """
    Create sample vendor data for testing and demonstration.
    
    Returns:
        List[ScrapingVendorData]: List of created vendor data records
    """
    service = setup_scraping_service()
    
    # Ensure table exists
    service.ensure_table_exists()
    
    sample_data = [
        {
            'product_name': 'Beras Premium',
            'price': '15000',
            'unit': 'kg',
            'vendor': 'Toko Sembako Jaya',
            'location': 'Jakarta Pusat'
        },
        {
            'product_name': 'Minyak Goreng',
            'price': '18000',
            'unit': 'liter',
            'vendor': 'Supermarket ABC',
            'location': 'Jakarta Selatan'
        },
        {
            'product_name': 'Gula Pasir',
            'price': '12000',
            'unit': 'kg',
            'vendor': 'Pasar Tradisional',
            'location': 'Jakarta Timur'
        },
        {
            'product_name': 'Telur Ayam',
            'price': '25000',
            'unit': 'kg',
            'vendor': 'Toko Sembako Jaya',
            'location': 'Jakarta Pusat'
        },
        {
            'product_name': 'Daging Sapi',
            'price': '120000',
            'unit': 'kg',
            'vendor': 'Pasar Modern',
            'location': 'Jakarta Barat'
        }
    ]
    
    created_records = []
    for data in sample_data:
        try:
            record = service.create_vendor_data(**data)
            created_records.append(record)
            print(f"Created: {record}")
        except Exception as e:
            print(f"Failed to create record {data['product_name']}: {e}")
    
    return created_records


def get_vendor_data_by_criteria(vendor: str = None, location: str = None) -> List[ScrapingVendorData]:
    """
    Retrieve vendor data by specific criteria.
    
    Args:
        vendor (str, optional): Filter by vendor name
        location (str, optional): Filter by location
        
    Returns:
        List[ScrapingVendorData]: Filtered vendor data records
    """
    service = setup_scraping_service()
    
    if vendor:
        return service.get_vendor_data_by_vendor(vendor)
    elif location:
        return service.get_vendor_data_by_location(location)
    else:
        return service.get_all_vendor_data()


def update_vendor_data_example(vendor_data_id: int) -> Optional[ScrapingVendorData]:
    """
    Example of updating vendor data.
    
    Args:
        vendor_data_id (int): ID of the vendor data to update
        
    Returns:
        Optional[ScrapingVendorData]: Updated vendor data or None if not found
    """
    service = setup_scraping_service()
    
    # Example update - change price
    updated_data = service.update_vendor_data(
        vendor_data_id,
        price='16000'  # Update price
    )
    
    if updated_data:
        print(f"Updated vendor data: {updated_data}")
    else:
        print(f"Vendor data with ID {vendor_data_id} not found")
    
    return updated_data


def search_products_by_name(product_name_keyword: str) -> List[ScrapingVendorData]:
    """
    Search for products containing a specific keyword in the name.
    
    Args:
        product_name_keyword (str): Keyword to search for in product names
        
    Returns:
        List[ScrapingVendorData]: Matching vendor data records
    """
    service = setup_scraping_service()
    all_data = service.get_all_vendor_data()
    
    # Filter by product name containing the keyword (case-insensitive)
    matching_data = [
        data for data in all_data 
        if product_name_keyword.lower() in data.product_name.lower()
    ]
    
    return matching_data


def get_price_comparison_by_product(product_name: str) -> List[dict]:
    """
    Get price comparison for a specific product across different vendors and locations.
    
    Args:
        product_name (str): Product name to compare prices for
        
    Returns:
        List[dict]: Price comparison data
    """
    service = setup_scraping_service()
    all_data = service.get_all_vendor_data()
    
    # Filter by exact product name (case-insensitive)
    product_data = [
        data for data in all_data 
        if data.product_name.lower() == product_name.lower()
    ]
    
    # Convert to comparison format
    comparison = []
    for data in product_data:
        comparison.append({
            'vendor': data.vendor,
            'location': data.location,
            'price': data.price,
            'unit': data.unit,
            'updated_at': data.updated_at
        })
    
    # Sort by price (assuming prices are numeric strings)
    try:
        comparison.sort(key=lambda x: float(x['price']))
    except ValueError:
        # If prices are not numeric, sort alphabetically
        comparison.sort(key=lambda x: x['price'])
    
    return comparison


def cleanup_test_data():
    """
    Clean up test data (delete all records).
    Use with caution - this will delete all vendor data!
    """
    service = setup_scraping_service()
    all_data = service.get_all_vendor_data()
    
    deleted_count = 0
    for data in all_data:
        if service.delete_vendor_data(data.id):
            deleted_count += 1
    
    print(f"Deleted {deleted_count} vendor data records")
    return deleted_count


def demonstrate_usage():
    """
    Demonstrate the usage of the scraping vendor data feature.
    """
    print("=== Scraping Vendor Data Feature Demonstration ===\n")
    
    # 1. Create sample data
    print("1. Creating sample vendor data...")
    created_records = create_sample_vendor_data()
    print(f"Created {len(created_records)} records\n")
    
    # 2. Get all data
    print("2. Retrieving all vendor data...")
    all_data = get_vendor_data_by_criteria()
    print(f"Total records: {len(all_data)}")
    for data in all_data:
        print(f"  - {data.product_name} @ {data.vendor} ({data.location}): {data.price} per {data.unit}")
    print()
    
    # 3. Filter by vendor
    print("3. Filtering by vendor 'Toko Sembako Jaya'...")
    vendor_data = get_vendor_data_by_criteria(vendor='Toko Sembako Jaya')
    for data in vendor_data:
        print(f"  - {data.product_name}: {data.price} per {data.unit}")
    print()
    
    # 4. Filter by location
    print("4. Filtering by location 'Jakarta Pusat'...")
    location_data = get_vendor_data_by_criteria(location='Jakarta Pusat')
    for data in location_data:
        print(f"  - {data.product_name} @ {data.vendor}: {data.price} per {data.unit}")
    print()
    
    # 5. Search products
    print("5. Searching for products containing 'Beras'...")
    beras_data = search_products_by_name('Beras')
    for data in beras_data:
        print(f"  - {data.product_name} @ {data.vendor} ({data.location}): {data.price} per {data.unit}")
    print()
    
    # 6. Price comparison
    print("6. Price comparison for 'Beras Premium'...")
    comparison = get_price_comparison_by_product('Beras Premium')
    for item in comparison:
        print(f"  - {item['vendor']} ({item['location']}): {item['price']} per {item['unit']}")
    print()
    
    # 7. Update example
    if created_records:
        print("7. Updating first record price...")
        update_vendor_data_example(created_records[0].id)
        print()
    
    print("=== Demonstration completed ===")


if __name__ == "__main__":
    # Run demonstration if this file is executed directly
    demonstrate_usage()