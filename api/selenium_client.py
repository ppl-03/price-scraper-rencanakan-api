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
    
    def __init__(self, headless=True, wait_timeout=10):
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.driver = None
        self._setup_driver()
    
    def _setup_driver(self):
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-images')  # Faster loading
            chrome_options.add_argument('--disable-javascript-harmony-shipping')
            
            # Set user agent to avoid detection
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            
            logger.info("Selenium WebDriver initialized successfully")
            
        except WebDriverException as e:
            raise HttpClientError(f"Failed to initialize WebDriver: {str(e)}")
    
    def get(self, url: str, timeout: int = None) -> str:
        if not self.driver:
            self._setup_driver()
        
        try:
            logger.info(f"Selenium fetching: {url}")
            
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, self.wait_timeout)
            
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='MuiGrid-item']")))
                
                wait.until(
                    lambda driver: (
                        driver.find_elements(By.CSS_SELECTOR, "span[class*='price']") or
                        driver.find_elements(By.CSS_SELECTOR, "a[class*='product']") or
                        driver.find_elements(By.CSS_SELECTOR, "[class*='gtm_mitra10']")
                    )
                )
                
                logger.info("JavaScript content loaded successfully")
                
            except TimeoutException:
                logger.warning("Timeout waiting for content to load, proceeding anyway")
            
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
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {str(e)}")
    
    def __del__(self):
        self.close()

class SeleniumSession:
    def __init__(self, headless=True, wait_timeout=10):
        self.client = SeleniumHttpClient(headless=headless, wait_timeout=wait_timeout)
    
    def __enter__(self):
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()