# Guide to Price Scraping on Vendor Websites


## Gemilang
https://gemilang-store.com/

#### **Directory Path**

`div.item-product` -> `div.price-wrapper` -> `p.price`

---

#### Path Breakdown

1.  **`div.item-product`**
    - This is the main container for an product card. Target the main container before attempting to scrape anything.

2.  **`div.price-wrapper`**
    - This is a child container inside a product card. It contains the price information, making it the focused area for scraping.

3.  **`p.price`**
    - This is the target element inside the `price-wrapper`. The text inside the`<p>` is the actual price of the product and should be scraped.


---
#### URL Breakdown

`https://gemilang-store.com/pusat/shop?keyword=ITEM&sort=price_asc&page=0`

he search term is controlled by the `keyword` parameter.

- **Parameter**: `keyword=ITEM`
- Search other itmes replace `ITEM` with serach keyword.

**Example**: To search for "", you would change the URL to:
`https://gemilang-store.com/pusat/shop?keyword=kayu`


#### 2. Sort Search

- **Parameter**: `sort=price_asc`
- The value `price_asc` will prioritize cheapest first
- To sort by **Price Descending** will find most expensive first.


## Depo Bangunan

[https://www.depobangunan.co.id/](https://www.depobangunan.co.id/)

#### **Directory Path**

`li.item.product.product-item` -> `div.product-item-info` -> `div.product.details.product-item-details` -> `div.price-box.price-final_price` 

#### For regular prices:
-> `span.price-wrapper[data-price-type="finalPrice"]` -> `span.price`

#### For discounted prices:
-> `span.special-price span.price-wrapper[data-price-type="finalPrice"]` -> `span.price`

---

#### Path Breakdown

1. **`li.item.product.product-item`**

   * Main container for a product card.

2. **`div.product-item-info`**

   * The main wrapper inside the card that groups image + details.

3. **`div.product.details.product-item-details`**

   * Holds product name, sold quantity, and price box.

4. **`div.price-box.price-final_price`**

   * Child container that stores the price section.

5. **`span.price-wrapper[data-price-type="finalPrice"]`**

   * Attribute `data-price-amount` contains the clean numeric price.

6. **`span.price`**

   * Visible formatted price (e.g., `Rp 3.600`).

7. **`span.special-price`**

    * Appears only if the product is discounted.
    * Contains the special (discounted) price.

---

#### URL Breakdown

`https://www.depobangunan.co.id/catalogsearch/result/?q=ITEM`

* **Parameter**: `q=ITEM`
  Replace `ITEM` with the search keyword.

**Example**: To search for cat:
`https://www.depobangunan.co.id/catalogsearch/result/?q=cat`

---


#### 2. Sort Search

* **Parameter**: `product_list_order=low_to_high`

  * Sorts results from lowest price to highest.

* **Parameter**: `product_list_order=high_to_low`

  * Sorts results from highest price to lowest.

**Example (search “cat”, cheapest first):**
`https://www.depobangunan.co.id/catalogsearch/result/index/?q=cat&product_list_order=low_to_high`



## Mitra10
https://www.mitra10.com/

#### **Directory Path**

`div.MuiGrid-item` → `div.grid-item` → `span.price__final`

---
#### Path Breakdown

1. **`div.MuiGrid-item`**
    - This is the main container for a product card.  

2.  **`div.grid-item`**
    - This is a child container inside the `MuiGrid-item`. Each `grid-item` represents an individual product, making it the focused area for scraping.

3.  **`span.price__final`**
    - This is the target element inside the `grid-item`. The text inside the `<span>` is the actual price of the product and should be scraped.


---
#### URL Breakdown

`https://www.mitra10.com/catalogsearch/result?q=ITEM&sort=%7B%22key%22:%22price%22,%22value%22:%22ASC%22%7D`

The search term is controlled by the `q` parameter.

- **Parameter**: `q=ITEM`
- Search other itmes replace `ITEM` with serach keyword.

**Example**: To search for a certain product, you can change the URL to:
`https://www.mitra10.com/catalogsearch/result?q=semen`


#### Sort Search

- **Parameter**: `sort=%7B%22key%22:%22price%22,%22value%22:%22ASC%22%7D`
- `ASC` will make the product sorted by cheapest first


## Juragan Material
https://juraganmaterial.id/

#### **Directory Path**

`div.product-card` -> `div.product-card-price` -> `div.price`

---

#### Path Breakdown

1.  **`div.product-card`**
    - This is the main container for each product listing on the page. It's the starting point for navigating to the specific product details.

2.  **`div.product-card-price`**
    - This is a child container within the product card. It holds the price and other related information, making it the area of focus.

3.  **`div.price`**
    - This is the specific element that contains the product's price. The text within this div should be scraped.


---
#### URL Breakdown

`https://juraganmaterial.id/produk?keyword=semen&page=1&sort=relevance`

the search term is controlled by the `keyword` parameter.

- **Parameter**: `keyword=ITEM`
- Search other itmes replace `ITEM` with serach keyword.

**Example**: To search for "cat", you would change the URL to:
`https://juraganmaterial.id/produk?keyword=cat`


#### 2. Sort Search

- **Parameter**: `sort=lowest_price`
- The value `lowest_price` will prioritize cheapest first
- To sort by **Highest Price** will find most expensive first.


## Tokopedia
https://www.tokopedia.com/

#### **Directory Path**

div[data-testid="lstCL2ProductList"] → a[data-testid="lnkProductContainer"] → div[data-testid="divProductWrapper"] → span.css-20kt3o → div → span.css-o5uqv

---

#### Path Breakdown

1. a[data-testid="lnkProductContainer"]
The clickable link container for each product. It wraps the entire product card including image, title, and price, and contains the href link to the product detail page.

2. div[data-testid="divProductWrapper"]
The inner product wrapper that holds all product content such as title, price, and shop information. This defines the layout and structure of each product card.

3. span.css-20kt3o
The product title element. It contains the product name text, for example: GRC BOARD 4MM PELAPON GRC ROYAL BOARD 6MM 8MM GRC 6MM GRC 8MM - GRC 4MM.

4. div
A nested container below the title span. It holds smaller UI components like the price label or any discount information.

5. span.css-o5uqv
The price element that displays the formatted price string, such as Rp55.670. This is the element you target when scraping product prices.

#### Complete Price Path:
a[data-testid="lnkProductContainer"] → div[data-testid="divProductWrapper"] → span.css-20kt3o → div → span.css-o5uqv

#### **Location Path - Multi-Strategy Extraction**

The Tokopedia location scraper uses a three-tier fallback strategy to extract merchant/seller location with maximum reliability:

**Priority 1 - Primary Selector (Most Reliable):**
- Selector: `span.css-ywdpwd` inside `div.css-vbihp9`
- Returns the inner text exactly as found on the page
- Example: `<span class="css-ywdpwd">Kab. Tangerang</span>` → `"Kab. Tangerang"`

**Priority 2 - Span Element Scan (Secondary Fallback):**
- When `css-ywdpwd` is not found, scan all span elements in document order
- Filter criteria:
  - Skip UI text (buttons like "Beli", "Tambah ke Wishlist", etc.)
  - Skip very short (< 3 chars) or very long (> 80 chars) text
  - Prioritize spans containing location keywords: `jakarta`, `bandung`, `surabaya`, `medan`, `semarang`, `yogyakarta`, `kab`, `kota`, `utara`, `selatan`, `timur`, `barat`, `pusat`, etc.
- Returns first valid location match in document order

**Priority 3 - Text Node Traversal (Final Fallback):**
- Last resort: extract location from raw text nodes
- Splits text by delimiters: `\n`, `\r`, `•`, `|`, `,`
- Two-pass approach:
  - First pass: look for segments containing known location keywords
  - Second pass: if no known location found, return first valid text segment
- Filters out obvious non-locations (product names, prices, etc.)

**Behavior & Notes:**

- Text is returned **exactly as found** on the page (preserves `Kab.`, `Kota.`, spacing, etc.)
- No aggressive normalization or database lookup is performed
- Invalid locations are rejected based on length constraints (2-100 chars) and content validation
- Optional field: returns `None` if no location can be extracted

**Example HTML Snippets:**

Primary method (preferred):
```html
<div class="css-vbihp9">
  <span class="css-ywdpwd">Jakarta Utara</span>
</div>
```
Expected output: `"location": "Jakarta Utara"`

Secondary method fallback (no css-ywdpwd class):
```html
<div class="product-item">
  <span>Product Name</span>
  <span>Jakarta Timur</span>
</div>
```
Expected output: `"location": "Jakarta Timur"`

Tertiary method fallback (text nodes):
```html
<div class="product-item">
  Product • Bandung | Shop
</div>
```
Expected output: `"location": "Bandung"`

**Rationale:**

- The multi-tier approach maximizes location extraction coverage while maintaining accuracy
- Prioritizing known location keywords in fallback methods reduces false-positives from UI elements
- Preserving original text format allows downstream systems to apply their own normalization if needed

**Recommendation:**

- For normalized or canonical location names (analytics, grouping, geo-lookup), implement a separate normalization pass that maps extracted strings to canonical names
- Do not modify the scraper's core extraction behavior to avoid losing site-provided context

#### Extracted Location Data:

The location field in the Product object contains:
- **Data Type**: String or None
- **Content**: Merchant/Seller Location (where the seller is based)
- **Format**: Returned as found on page (e.g., "Jakarta Utara", "Kab. Bandung", "Kota Surabaya")
- **Extraction Method**: Multi-strategy approach (css-ywdpwd selector → span scan → text node traversal)
- **Availability**: Optional field (None if extraction unsuccessful across all strategies)
- **Use Case**: Understanding product availability, estimating shipping times, and filtering by seller location

#### Common Locations Found:
- "Jakarta Utara", "Jakarta Selatan", "Jakarta Timur", "Jakarta Barat", "Jakarta Pusat"
- "Bandung", "Surabaya", "Medan", "Semarang", "Yogyakarta"
- "Makassar", "Tangerang", "Depok", "Bekasi", "Bogor"
- "Kab. Tangerang", "Kab. Bandung", "Kota Bandung"
- And 100+ other major Indonesian cities and regencies

---

#### URL Breakdown

`https://www.tokopedia.com/p/pertukangan/material-bangunan?page=1&q=semen&ob=3`

The search term is controlled by the `q` parameter.

- **Parameter**: `q=ITEM`
- Search other items by replacing `ITEM` with search keyword. Use `+` for spaces.

**Example**: To search for "semen" in material bangunan category:
`https://www.tokopedia.com/p/pertukangan/material-bangunan?page=1&q=semen`

#### 2. Sort Search

- **Parameter**: `ob=3` - Sort by lowest price first
- **Parameter**: `ob=4` - Sort by highest price first  
- **Parameter**: `ob=5` - Sort by review/rating
- **Parameter**: `ob=9` - Sort by newest products
- **Parameter**: `ob=23` - Sort by most relevant (default)

**Example (search "semen" in category, cheapest first):**
`https://www.tokopedia.com/p/pertukangan/material-bangunan?q=semen&ob=3`

#### 3. Additional Parameters

- **Parameter**: `page=1` - Page number for pagination
- **Parameter**: `pmin=10000` - Minimum price filter
- **Parameter**: `pmax=100000` - Maximum price filter
- **Parameter**: `rt=4,5` - Rating filter (4+ stars)
- **Parameter**: `fcity=176` - Location filter (city ID)

**Example with price filter (general search):**
`https://www.tokopedia.com/search?q=material+bangunan&ob=3&pmin=10000&pmax=50000`

**Example with price filter (category search):**
`https://www.tokopedia.com/p/pertukangan/material-bangunan?q=semen&ob=3&pmin=10000&pmax=50000`

---

#### Category Path Structure

For material bangunan (construction materials), use the category path:
- **Category URL**: `/p/pertukangan/material-bangunan`
- **Benefits**: 
  - More relevant results within the category
  - Better filtering options specific to construction materials
  
---

#### Note on Dynamic Loading
Tokopedia uses dynamic JavaScript loading for search results. The product containers may load asynchronously, requiring:
- Wait for DOM elements to be fully loaded
- Handle infinite scroll pagination
- Consider using browser automation tools (Selenium/Playwright) for reliable scraping