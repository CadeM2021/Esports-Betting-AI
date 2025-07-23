import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def init_driver():
    """Bulletproof ChromeDriver initialization for Streamlit Cloud"""
    try:
        options = Options()
        
        # Required for Streamlit Cloud/Docker
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage") 
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        
        # Anti-bot measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Set explicit binary paths (critical)
        options.binary_location = "/usr/bin/google-chrome"
        service = Service(executable_path="/usr/bin/chromedriver")
        
        # Initialize driver
        driver = webdriver.Chrome(service=service, options=options)
        
        # Configure timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)
        
        return driver
        
    except Exception as e:
        print(f"CRITICAL DRIVER ERROR: {str(e)}", file=sys.stderr)
        raise RuntimeError("Browser initialization failed. Please check the logs for details.")
        
        return driver
        
    except Exception as e:
        logging.error(f"ChromeDriver initialization failed: {str(e)}")
        raise RuntimeError("Failed to initialize browser. Please check logs and try again later.")
