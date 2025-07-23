import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging

def init_driver():
    """Initialize ChromeDriver with comprehensive error handling"""
    try:
        options = Options()
        
        # Required for Docker/Streamlit Cloud
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        
        # Anti-detection settings
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Set explicit paths (critical for Docker)
        chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
        options.binary_location = chrome_bin
        
        # Initialize driver with automatic management
        service = Service(executable_path=os.getenv("CHROME_DRIVER", "/usr/bin/chromedriver"))
        driver = webdriver.Chrome(service=service, options=options)
        
        # Configure timeouts
        driver.set_page_load_timeout(45)
        driver.implicitly_wait(5)
        
        return driver
        
    except Exception as e:
        logging.error(f"ChromeDriver initialization failed: {str(e)}")
        raise RuntimeError("Failed to initialize browser. Please check logs and try again later.")
