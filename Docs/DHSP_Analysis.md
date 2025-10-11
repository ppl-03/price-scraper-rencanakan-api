# Guide to Price Scraping on Government Wage Websites

## MAS PETRUK - Central Java Government Wage System
https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk#

#### **Directory Path**

`table.dataTable` -> `tbody` -> `tr` -> `td` (for each data column)

---

#### Path Breakdown

1. **`table.dataTable`**
   - This is the main data table container that holds all government wage information. Uses DataTables framework for dynamic functionality.

2. **`tbody`**
   - The table body that contains all data rows. Each row represents one work item with its pricing information.

3. **`tr`** 
   - Individual table rows, each containing a complete work item record with code, description, unit, and price.

4. **`td` columns breakdown:**
   - `td:nth-child(1)` - Sequential number (No.)
   - `td:nth-child(2)` - Work item code (Kode)
   - `td:nth-child(3)` - Work description (Uraian Pekerjaan)
   - `td:nth-child(4)` - Unit of measurement (Satuan)
   - `td:nth-child(5)` - Unit price in IDR (Harga Satuan)

---

#### URL Breakdown

`https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk#`

Base URL for accessing the government wage system. Additional parameters may be required for region selection and data filtering.

**Region Selection:**
- System appears to have dropdown for different regencies
- Current visible region: `Kab. Cilacap` (Cilacap Regency)
- Other regions may require dynamic selection

**Example region access pattern:**
```
Base: https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk
Region parameter: [Requires investigation of AJAX calls]
```

---

#### Search and Filter Capabilities

**1. Text Search**
- **Feature**: General search box available
- **Target**: Searches across work descriptions and codes
- **Implementation**: Likely uses DataTables search API

**2. Column Sorting**
- **Feature**: All columns sortable (↑↓ arrows visible)
- **Columns**: No., Kode, Uraian Pekerjaan, Satuan, Harga Satuan
- **Direction**: Ascending/Descending for each column

**3. Region Filter**
- **Feature**: Dropdown selection for different regencies
- **Current**: Kab. Cilacap
- **Scope**: Central Java Province (Provinsi Jawa Tengah)

---

#### Dynamic Content Handling

**1. AJAX Data Loading**
```javascript
// Expected behavior:
// - Data loads dynamically via AJAX calls
// - Table shows "Sedang memproses..." (Processing) during load
// - "Tidak ditemukan data yang sesuai" when no results
```

**2. Pagination**
- **Navigation**: Previous/Next buttons
- **Status**: Shows "Menampilkan X sampai Y dari Z entri"
- **Current State**: "Menampilkan 0 sampai 0 dari 0 entri" (no data loaded)

**3. Session Requirements**
- May require proper session handling for sustained access
- Government sites often have security measures

---

#### Data Structure Schema

```json
{
  "item_number": "Sequential number in table",
  "work_code": "Government standardized work code",
  "work_description": "Detailed specification of construction work",
  "unit": "Measurement unit (m², m³, kg, etc.)",
  "unit_price_idr": "Price in Indonesian Rupiah",
  "region": "Regency/Municipality code",
  "edition": "Price list edition (currently: Edisi Ke - 2)",
  "year": "Publication year (currently: 2024)",
  "sector": "Bidang Cipta Karya dan Perumahan"
}
```

---

#### Technical Considerations

**1. JavaScript Dependency**
- Site requires JavaScript execution for data loading
- Use Playwright or Selenium for proper rendering

**2. Rate Limiting**
- Government site - implement respectful request delays
- Recommended: 2-3 seconds between requests
- Monitor for any blocking or captcha systems

**3. Region Iteration Strategy**
```python
# Pseudo-code for region handling:
regions = get_available_regions()  # Extract from dropdown
for region in regions:
    select_region(region)
    wait_for_data_load()
    scrape_table_data()
    save_with_region_info(data, region)
```

**4. Error Handling**
- Handle "Tidak ditemukan data yang sesuai" (No data found)
- Manage timeout during "Sedang memproses..." (Processing)
- Implement retry logic for failed requests

---

#### Government Data Compliance

**1. Data Attribution**
- **Source**: Dinas PU Bina Marga dan Cipta Karya
- **Publisher**: Balai Jasa Konstruksi Provinsi Jawa Tengah
- **Address**: Jl. Ace No.3, Srondol Wetan, Kec. Banyumanik, Kota Semarang

**2. Usage Guidelines**
- Public government information (HSPK data)
- Proper attribution required in any derivative work
- Respectful access patterns mandatory
- Data integrity preservation essential

**3. Update Schedule**
- **Current Edition**: 2nd Edition, Year 2024
- **Update Frequency**: Appears to be annual
- **Version Tracking**: Monitor for new editions

---

#### Implementation Priority

**High Priority:**
1. JavaScript-enabled scraping setup (Playwright recommended)
2. Dynamic content loading handling
3. Region selection automation
4. Data validation and cleaning

**Medium Priority:**
1. Pagination navigation
2. Search functionality implementation
3. Error state handling
4. Rate limiting compliance

**Low Priority:**
1. Historical data comparison
2. Multi-year data archiving
3. Cross-region price analysis