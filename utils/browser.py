import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def init_driver(headless=True):
    """
    Initialize ChromeDriver with Docker/Streamlit Cloud compatibility
    Returns:
        WebDriver: Configured ChromeDriver instance
    Raises:
        RuntimeError: If driver initialization fails
    """
    options = Options()
    
    # Required for Docker/Streamlit Cloud
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # Set explicit paths from Dockerfile
    options.binary_location = "/usr/bin/google-chrome"
    
    if headless:
        options.add_argument("--headless=new")

    # Anti-bot and optimization settings
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        # Use the system chromedriver from Docker installation
        service = Service(executable_path="/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set timeouts (in seconds)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)
        
        return driver
        
    except Exception as e:
        raise RuntimeError(f"🚨 ChromeDriver init failed: {str(e)}")
