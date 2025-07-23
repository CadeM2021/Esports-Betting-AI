import streamlit as st
import pandas as pd
import numpy as np
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
from scipy import stats
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pyvirtualdisplay import Display
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
UNDERDOG_URL = "https://underdogfantasy.com/pick-em/higher-lower/all/val"
VLR_URL = "https://www.vlr.gg/matches"
CACHE_DURATION = 1800  # 30 minutes in seconds

# ========== SELENIUM SETUP ==========
def setup_selenium():
    """Configure and return a Selenium WebDriver"""
    try:
        # For Linux environments (like Streamlit Cloud)
        display = Display(visible=0, size=(1920, 1080))
        display.start()
    except Exception as e:
        logger.warning(f"Virtual display not available: {e}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager(version="114.0.5735.90").install()),
            options=chrome_options
        )
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {e}")
        st.error("Failed to initialize browser automation. Please try again later.")
        return None

# ========== SCRAPING FUNCTIONS ==========
def scrape_underdog():
    """Scrape player data from Underdog Fantasy"""
    # First try with HTTP requests
    try:
        with httpx.Client() as client:
            response = client.get(UNDERDOG_URL, headers=HEADERS, timeout=20.0)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            players = []
            for card in soup.select('div[class*="player-line"]'):
                try:
                    players.append({
                        'name': card.select_one('div[class*="player-name"]').text.strip(),
                        'line': float(card.select_one('div[class*="line-value"]').text.strip()),
                        'team': card.select_one('div[class*="player-team"]').text.strip(),
                        'scraped_at': datetime.now(pytz.UTC)
                    })
                except Exception as e:
                    logger.warning(f"Error parsing player card: {e}")
                    continue
            return pd.DataFrame(players)
    except Exception as e:
        logger.warning(f"HTTP scrape failed, falling back to Selenium: {e}")
        
        # Fall back to Selenium
        driver = setup_selenium()
        if not driver:
            return pd.DataFrame()
            
        try:
            driver.get(UNDERDOG_URL)
            time.sleep(5)  # Wait for page to load
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            players = []
            for card in soup.select('div[class*="player-line"]'):
                try:
                    players.append({
                        'name': card.select_one('div[class*="player-name"]').text.strip(),
                        'line': float(card.select_one('div[class*="line-value"]').text.strip()),
                        'team': card.select_one('div[class*="player-team"]').text.strip(),
                        'scraped_at': datetime.now(pytz.UTC)
                    })
                except Exception as e:
                    logger.warning(f"Error parsing player card: {e}")
                    continue
            return pd.DataFrame(players)
        except Exception as e:
            logger.error(f"Selenium scrape failed: {e}")
            return pd.DataFrame()
        finally:
            driver.quit()

def scrape_vlr_matches():
    """Scrape upcoming matches from VLR.gg"""
    try:
        with httpx.Client() as client:
            response = client.get(VLR_URL, headers=HEADERS, timeout=20.0)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            matches = []
            for match in soup.select('a.match-item'):
                try:
                    matches.append({
                        'team1': match.select_one('div.mod-1').text.strip(),
                        'team2': match.select_one('div.mod-2').text.strip(),
                        'event': match.select_one('div.match-item-event').text.strip(),
                        'time': match.select_one('div.match-item-time').text.strip(),
                        'link': f"https://www.vlr.gg{match['href']}"
                    })
                except Exception as e:
                    logger.warning(f"Error parsing match: {e}")
                    continue
            return pd.DataFrame(matches)
    except Exception as e:
        logger.error(f"VLR scrape failed: {e}")
        return pd.DataFrame()

# ========== PREDICTION ENGINE ==========
def calculate_predictions(lines_df, matches_df):
    """Generate predictions based on scraped data"""
    if lines_df.empty or matches_df.empty:
        return pd.DataFrame()
        
    predictions = []
    for _, row in lines_df.iterrows():
        try:
            # Find matching game
            match = matches_df[
                (matches_df['team1'].str.contains(row['team'], case=False)) | 
                (matches_df['team2'].str.contains(row['team'], case=False))
            ].iloc[0]
            
            opponent = match['team2'] if match['team1'].lower() == row['team'].lower() else match['team1']
            
            # Simple prediction model (can be enhanced)
            mu = row['line'] * 1.1  # Expected mean
            sigma = 2.5  # Standard deviation
            prob_over = 1 - stats.norm.cdf(row['line'], mu, sigma)
            
            predictions.append({
                'Player': row['name'],
                'Line': row['line'],
                'Team': row['team'],
                'Opponent': opponent,
                'Event': match['event'],
                'Time': match['time'],
                'P(OVER)': f"{prob_over:.0%}",
                'Verdict': "OVER" if prob_over > 0.6 else "UNDER",
                'Confidence': "High" if abs(prob_over - 0.5) > 0.3 else "Medium"
            })
        except Exception as e:
            logger.warning(f"Prediction error for {row['name']}: {e}")
            continue
            
    return pd.DataFrame(predictions)

# ========== STREAMLIT UI ==========
def main():
    st.set_page_config(
        page_title="VALORANT Betting AI",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🔫 VALORANT Betting AI")
    st.markdown("""
    This app scrapes betting lines from Underdog Fantasy and matches from VLR.gg, 
    then generates predictions using statistical models.
    """)
    
    if st.button("🔄 Refresh Data", help="Click to fetch the latest data"):
        with st.spinner("Loading data..."):
            # Scrape data
            lines_df = scrape_underdog()
            matches_df = scrape_vlr_matches()
            
            # Generate predictions
            predictions_df = calculate_predictions(lines_df, matches_df)
            
            # Cache results in session state
            st.session_state['predictions'] = predictions_df
            st.session_state['last_update'] = datetime.now()
    
    # Display results if available
    if 'predictions' in st.session_state and not st.session_state['predictions'].empty:
        st.subheader("Latest Predictions")
        
        # Color coding for verdicts
        def color_verdict(val):
            color = 'green' if val == "OVER" else 'red'
            return f'color: {color}'
        
        styled_df = st.session_state['predictions'].style.applymap(
            color_verdict, subset=['Verdict']
        )
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        
        if 'last_update' in st.session_state:
            st.caption(f"Last updated: {st.session_state['last_update'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.warning("No data available. Click 'Refresh Data' to fetch predictions.")
    
    # Add some analytics
    if 'predictions' in st.session_state:
        st.subheader("Prediction Analytics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Predictions", len(st.session_state['predictions']))
        
        with col2:
            over_count = sum(st.session_state['predictions']['Verdict'] == "OVER")
            st.metric("OVER Recommendations", over_count)
        
        with col3:
            high_conf = sum(st.session_state['predictions']['Confidence'] == "High")
            st.metric("High Confidence Picks", high_conf)

if __name__ == "__main__":
    main()
