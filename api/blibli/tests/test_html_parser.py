import unittest
from api.blibli.html_parser import BlibliHtmlParser
from api.interfaces import Product

class TestBlibliHtmlParser(unittest.TestCase):
    def setUp(self):
        self.parser = BlibliHtmlParser()

    def test_parse_single_product(self):
        html = '''
<div class="product-list__card">
  <div class="elf-product-card__container">
    <a class="elf-product-card" href="/p/test-product">
      <div class="els-product white-background">
        <div class="els-product_image-wrapper"></div>
        <div class="els-product__info">
          <div class="els-product__title-wrapper">
            <span class="els-product__title" title="Test Product Name">
              <span>Test Product Name</span>
            </span>
          </div>
          <div class="els-product__price-wrapper">
            <div class="els-product__price-top">
              <div class="els-product__fixed-price-wrapper">
                <div class="els-product__fixed-price" title="12.345">
                  <span class="els-product__fixed-price-label">Rp</span>
                  <span>12.345</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a>
  </div>
</div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product.name, "Test Product Name")
        self.assertEqual(product.price, 12345)
        self.assertEqual(product.url, "/p/test-product")

    def test_parse_no_products(self):
        html = '<div></div>'
        products = self.parser.parse_products(html)
        self.assertEqual(products, [])

    def test_parse_missing_price(self):
        html = '''
<div class="product-list__card">
  <div class="elf-product-card__container">
    <a class="elf-product-card" href="/p/test-product">
      <div class="els-product white-background">
        <div class="els-product_image-wrapper"></div>
        <div class="els-product__info">
          <div class="els-product__title-wrapper">
            <span class="els-product__title" title="Test Product Name">
              <span>Test Product Name</span>
            </span>
          </div>
        </div>
      </div>
    </a>
  </div>
</div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(products, [])

    def test_parse_missing_name(self):
        html = '''
<div class="product-list__card">
  <div class="elf-product-card__container">
    <a class="elf-product-card" href="/p/test-product">
      <div class="els-product white-background">
        <div class="els-product_image-wrapper"></div>
        <div class="els-product__info">
          <div class="els-product__price-wrapper">
            <div class="els-product__price-top">
              <div class="els-product__fixed-price-wrapper">
                <div class="els-product__fixed-price" title="12.345">
                  <span class="els-product__fixed-price-label">Rp</span>
                  <span>12.345</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a>
  </div>
</div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(products, [])

    def test_parse_multiple_products(self):
        html = '''
<div class="product-list__card">
  <div class="elf-product-card__container">
    <a class="elf-product-card" href="/p/product1">
      <div class="els-product white-background">
        <div class="els-product_image-wrapper"></div>
        <div class="els-product__info">
          <div class="els-product__title-wrapper">
            <span class="els-product__title" title="Product 1">
              <span>Product 1</span>
            </span>
          </div>
          <div class="els-product__price-wrapper">
            <div class="els-product__price-top">
              <div class="els-product__fixed-price-wrapper">
                <div class="els-product__fixed-price" title="10.000">
                  <span class="els-product__fixed-price-label">Rp</span>
                  <span>10.000</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a>
  </div>
</div>
<div class="product-list__card">
  <div class="elf-product-card__container">
    <a class="elf-product-card" href="/p/product2">
      <div class="els-product white-background">
        <div class="els-product_image-wrapper"></div>
        <div class="els-product__info">
          <div class="els-product__title-wrapper">
            <span class="els-product__title" title="Product 2">
              <span>Product 2</span>
            </span>
          </div>
          <div class="els-product__price-wrapper">
            <div class="els-product__price-top">
              <div class="els-product__fixed-price-wrapper">
                <div class="els-product__fixed-price" title="20.000">
                  <span class="els-product__fixed-price-label">Rp</span>
                  <span>20.000</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a>
  </div>
</div>
        '''
        products = self.parser.parse_products(html)
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].name, "Product 1")
        self.assertEqual(products[0].price, 10000)
        self.assertEqual(products[0].url, "/p/product1")
        self.assertEqual(products[1].name, "Product 2")
        self.assertEqual(products[1].price, 20000)
        self.assertEqual(products[1].url, "/p/product2")

if __name__ == '__main__':
    unittest.main()
