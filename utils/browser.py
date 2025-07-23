import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

def init_driver():
    """Robust ChromeDriver initialization with multiple fallbacks"""
    options = Options()
    
    # Essential configuration for headless operation
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # Anti-bot measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        # Attempt to use webdriver-manager's built-in Chrome binaries
        return webdriver.Chrome(
            service=Service(ChromeDriverManager(
                chrome_type=ChromeType.CHROMIUM
            ).install()),
            options=options
        )
    except Exception as e:
        print(f"CRITICAL DRIVER ERROR: {str(e)}", file=sys.stderr)
        return None  # Graceful fallback
