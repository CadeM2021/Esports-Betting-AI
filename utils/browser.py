import os
import sys
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def init_driver():
    """Initialize ChromeDriver with multiple fallback strategies"""
    options = configure_chrome_options()
    
    # Ordered list of initialization methods to try
    init_methods = [
        try_system_chrome,
        try_webdriver_manager,
        try_chromium
    ]
    
    for method in init_methods:
        driver = method(options)
        if driver is not None:
            logger.info(f"Successfully initialized using {method.__name__}")
            return driver
    
    logger.error("All ChromeDriver initialization methods failed")
    return None

def configure_chrome_options():
    """Configure Chrome options for headless scraping"""
    options = Options()
    
    # Base configuration
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # Anti-bot measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Performance optimizations
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-notifications")
    
    return options

def try_system_chrome(options):
    """Attempt using system-installed Chrome"""
    try:
        if os.path.exists("/usr/bin/google-chrome"):
            options.binary_location = "/usr/bin/google-chrome"
            service = Service("/usr/bin/chromedriver")
            return webdriver.Chrome(service=service, options=options)
    except Exception as e:
        logger.warning(f"System Chrome failed: {str(e)}")
    return None

def try_webdriver_manager(options):
    """Attempt using webdriver-manager with standard Chrome"""
    try:
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
    except Exception as e:
        logger.warning(f"Webdriver Manager (Chrome) failed: {str(e)}")
    return None

def try_chromium(options):
    """Fallback to Chromium if Chrome fails"""
    try:
        return webdriver.Chrome(
            service=Service(ChromeDriverManager(
                chrome_type=ChromeType.CHROMIUM
            ).install()),
            options=options
        )
    except Exception as e:
        logger.warning(f"Webdriver Manager (Chromium) failed: {str(e)}")
    return None

# Test function for local debugging
if __name__ == "__main__":
    driver = init_driver()
    if driver:
        print("Successfully initialized ChromeDriver!")
        driver.quit()
    else:
        print("Failed to initialize ChromeDriver")
