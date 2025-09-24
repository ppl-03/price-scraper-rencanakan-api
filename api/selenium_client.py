#!/usr/bin/env python
"""
Selenium-based HTTP Client for JavaScript-heavy websites
"""
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from api.interfaces import IHttpClient, HttpClientError

logger = logging.getLogger(__name__)

class SeleniumHttpClient(IHttpClient):
    """HTTP client that uses Selenium to handle JavaScript rendering"""
    
    def __init__(self, headless=True, wait_timeout=10):
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.driver = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Setup Chrome WebDriver with optimal settings"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            # Optimize for scraping
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-images')  # Faster loading
            chrome_options.add_argument('--disable-javascript-harmony-shipping')
            
            # Set user agent to avoid detection
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # You may need to specify chromedriver path
            # service = Service('/path/to/chromedriver')  # Uncomment and set path if needed
            # self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            
            logger.info("Selenium WebDriver initialized successfully")
            
        except WebDriverException as e:
            raise HttpClientError(f"Failed to initialize WebDriver: {str(e)}")
    
    def get(self, url: str, timeout: int = None) -> str:
        """Fetch URL and wait for JavaScript content to load"""
        if not self.driver:
            self._setup_driver()
        
        try:
            logger.info(f"Selenium fetching: {url}")
            
            # Load the page
            self.driver.get(url)
            
            # Wait for content to load - look for product containers
            wait = WebDriverWait(self.driver, self.wait_timeout)
            
            # Wait for either products to load OR skeleton loaders to disappear
            try:
                # First, wait for the main container
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='MuiGrid-item']")))
                
                # Then wait for actual content (not skeleton loaders)
                # Look for price elements or product links
                wait.until(
                    lambda driver: (
                        driver.find_elements(By.CSS_SELECTOR, "span[class*='price']") or
                        driver.find_elements(By.CSS_SELECTOR, "a[class*='product']") or
                        driver.find_elements(By.CSS_SELECTOR, "[class*='gtm_mitra10']")
                    )
                )
                
                logger.info("JavaScript content loaded successfully")
                
            except TimeoutException:
                logger.warning(f"Timeout waiting for content to load, proceeding anyway")
            
            # Additional wait to ensure all content is loaded
            time.sleep(2)
            
            # Get the page source after JavaScript execution
            html_content = self.driver.page_source
            
            logger.info(f"Retrieved {len(html_content)} characters from {url}")
            return html_content
            
        except WebDriverException as e:
            raise HttpClientError(f"Selenium error for {url}: {str(e)}")
        except Exception as e:
            raise HttpClientError(f"Unexpected error fetching {url}: {str(e)}")
    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.close()

# Context manager for automatic cleanup
class SeleniumSession:
    def __init__(self, headless=True, wait_timeout=10):
        self.client = SeleniumHttpClient(headless=headless, wait_timeout=wait_timeout)
    
    def __enter__(self):
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()