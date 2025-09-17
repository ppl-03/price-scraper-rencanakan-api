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

