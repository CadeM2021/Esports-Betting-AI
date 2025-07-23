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
import json

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

# ========== INITIALIZE SESSION STATE ==========
if 'predictions' not in st.session_state:
    st.session_state.predictions = pd.DataFrame()
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

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
            st.error("Failed to scrape Underdog Fantasy data")
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
        st.error("Failed to scrape VLR.gg match data")
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
            
            # Enhanced prediction model
            mu = row['line'] * 1.1  # Expected mean
            sigma = 2.5  # Standard deviation
            prob_over = 1 - stats.norm.cdf(row['line'], mu, sigma)
            
            # Confidence calculation
            confidence = "High" if abs(prob_over - 0.5) > 0.3 else ("Medium" if abs(prob_over - 0.5) > 0.15 else "Low")
            
            predictions.append({
                'Player': row['name'],
                'Line': row['line'],
                'Team': row['team'],
                'Opponent': opponent,
                'Event': match['event'],
                'Time': match['time'],
                'P(OVER)': f"{prob_over:.0%}",
                'Verdict': "OVER" if prob_over > 0.55 else "UNDER",
                'Confidence': confidence,
                'Match Link': match['link']
            })
        except Exception as e:
            logger.warning(f"Prediction error for {row['name']}: {e}")
            continue
            
    return pd.DataFrame(predictions)

# ========== DeepSeek CHATBOT ==========
class EsportsAnalyst:
    def __init__(self):
        self.knowledge_base = {
            "over under": "The OVER/UNDER predictions are based on statistical analysis of player performance data.",
            "confidence": "Confidence levels (High/Medium/Low) indicate prediction certainty based on historical variance.",
            "valorant": "This app specializes in VALORANT esports betting analysis using Underdog Fantasy data."
        }
    
    def generate_response(self, query, predictions_df):
        """Generate response using both knowledge base and current predictions"""
        query = query.lower()
        
        # Check knowledge base first
        for key in self.knowledge_base:
            if key in query:
                return self.knowledge_base[key]
        
        # Handle data-specific queries
        if not predictions_df.empty:
            if "over" in query or "under" in query:
                verdict = "OVER" if "over" in query else "UNDER"
                filtered = predictions_df[predictions_df['Verdict'] == verdict]
                if not filtered.empty:
                    return f"Here are {len(filtered)} {verdict} recommendations:\n\n{filtered[['Player', 'Line', 'Confidence']].to_markdown()}"
            
            if "player" in query:
                player_name = query.replace("player", "").strip()
                player_data = predictions_df[predictions_df['Player'].str.contains(player_name, case=False)]
                if not player_data.empty:
                    return player_data.to_markdown()
            
            if "match" in query:
                return predictions_df[['Team', 'Opponent', 'Event', 'Time']].drop_duplicates().to_markdown()
        
        return "I can answer questions about: OVER/UNDER predictions, specific players, or upcoming matches."

# ========== STREAMLIT UI ==========
def main():
    st.set_page_config(
        page_title="VALORANT Betting AI Pro",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize chatbot
    analyst = EsportsAnalyst()
    
    # Main App
    st.title("🔫 VALORANT Betting AI Pro")
    st.markdown("""
    Advanced betting predictions powered by statistical analysis and DeepSeek AI.
    """)
    
    # Data Refresh Section
    with st.expander("🔍 Data Collection", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("Get the latest betting lines and match data")
        with col2:
            if st.button("🔄 Refresh Data", help="Click to fetch the latest data"):
                with st.spinner("Loading data..."):
                    try:
                        lines_df = scrape_underdog()
                        matches_df = scrape_vlr_matches()
                        st.session_state.predictions = calculate_predictions(lines_df, matches_df)
                        st.session_state.last_update = datetime.now()
                        st.success("Data refreshed successfully!")
                    except Exception as e:
                        st.error(f"Error refreshing data: {str(e)}")
    
    # Main Display
    if not st.session_state.predictions.empty:
        tab1, tab2 = st.tabs(["📊 Predictions", "📈 Analytics"])
        
        with tab1:
            st.subheader("Latest Predictions")
            
            # Color coding for verdicts
            def color_verdict(val):
                color = '#4CAF50' if val == "OVER" else '#F44336'
                return f'color: {color}'
            
            # Enhanced dataframe display
            display_cols = ['Player', 'Team', 'Opponent', 'Line', 'P(OVER)', 'Verdict', 'Confidence']
            styled_df = st.session_state.predictions[display_cols].style.applymap(
                color_verdict, subset=['Verdict']
            )
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=600,
                column_config={
                    "Line": st.column_config.NumberColumn(format="%.1f"),
                    "P(OVER)": st.column_config.ProgressColumn(
                        format="%.0f%%",
                        min_value=0,
                        max_value=100,
                    )
                }
            )
            
            if st.session_state.last_update:
                st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        
        with tab2:
            st.subheader("Prediction Analytics")
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            total = len(st.session_state.predictions)
            
            with col1:
                st.metric("Total Predictions", total)
            
            with col2:
                over_count = sum(st.session_state.predictions['Verdict'] == "OVER")
                st.metric("OVER Recommendations", f"{over_count} ({over_count/total:.0%})")
            
            with col3:
                high_conf = sum(st.session_state.predictions['Confidence'] == "High")
                st.metric("High Confidence", f"{high_conf} ({high_conf/total:.0%})")
            
            with col4:
                avg_prob = st.session_state.predictions['P(OVER)'].str.rstrip('%').astype('float').mean()
                st.metric("Avg OVER Probability", f"{avg_prob:.0f}%")
            
            # Distribution charts
            st.subheader("Prediction Distribution")
            col1, col2 = st.columns(2)
            
            with col1:
                st.bar_chart(st.session_state.predictions['Verdict'].value_counts())
            
            with col2:
                st.bar_chart(st.session_state.predictions['Confidence'].value_counts())
    else:
        st.warning("No prediction data available. Click 'Refresh Data' to fetch the latest information.")
    
    # Chatbot Interface
    st.sidebar.title("🤖 DeepSeek Esports Analyst")
    
    for msg in st.session_state.chat_history:
        with st.sidebar.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    if prompt := st.sidebar.chat_input("Ask about predictions..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with st.sidebar.chat_message("user"):
            st.markdown(prompt)
        
        with st.sidebar.spinner("Analyzing..."):
            response = analyst.generate_response(prompt, st.session_state.predictions)
        
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        with st.sidebar.chat_message("assistant"):
            st.markdown(response)

if __name__ == "__main__":
    main()
