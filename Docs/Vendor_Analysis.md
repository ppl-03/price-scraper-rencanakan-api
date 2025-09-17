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

`li.item.product.product-item` -> `div.product-item-info` -> `div.product.details.product-item-details` -> `div.price-box.price-final_price` -> `span.price-wrapper[data-price-type="finalPrice"]` -> `span.price`

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