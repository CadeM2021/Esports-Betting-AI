import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pyvirtualdisplay import Display
from bs4 import BeautifulSoup
import pytz
from datetime import datetime

def setup_selenium():
    """Robust Selenium setup that works on Streamlit Cloud"""
    try:
        # For Linux environments (like Streamlit Cloud)
        display = Display(visible=0, size=(1920, 1080))
        display.start()
    except:
        pass  # Will work locally without this

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")

    # Fixed ChromeDriver version for stability
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager(version="114.0.5735.90").install()),
        options=chrome_options
    )
    return driver

def scrape_underdog_with_selenium():
    """More resilient scraping function"""
    try:
        driver = setup_selenium()
        driver.get("https://underdogfantasy.com/pick-em/higher-lower/all/val")
        time.sleep(5)  # Wait for page to load
        
        # More robust element selection
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        players = []
        
        for card in soup.select('div[class*="player-line"]'):
            try:
                name = card.select_one('div[class*="player-name"]').text.strip()
                line = float(card.select_one('div[class*="line-value"]').text.strip())
                team = card.select_one('div[class*="player-team"]').text.strip()
                
                players.append({
                    'name': name,
                    'line': line,
                    'team': team,
                    'scraped_at': datetime.now(pytz.UTC)
                })
            except Exception as e:
                st.warning(f"Skipping player due to error: {str(e)}")
                continue
                
        return pd.DataFrame(players)
        
    except Exception as e:
        st.error(f"Scraping failed: {str(e)}")
        return pd.DataFrame()
    finally:
        if 'driver' in locals():
            driver.quit()

def main():
    st.title("eSports Betting AI")
    
    if st.button("Scrape Underdog Data"):
        with st.spinner("Scraping data..."):
            df = scrape_underdog_with_selenium()
            
        if not df.empty:
            st.success(f"Successfully scraped {len(df)} players!")
            st.dataframe(df)
        else:
            st.error("No data was scraped. Check the logs for errors.")

if __name__ == "__main__":
    main()
