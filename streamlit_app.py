# valorant_analyst.py
import streamlit as st
import pandas as pd
import numpy as np
import httpx
from bs4 import BeautifulSoup
import time
import random
from fake_useragent import UserAgent
from scipy.stats import norm
import logging
from datetime import datetime, timezone
import plotly.express as px
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ------------------------------
# CONFIGURATION
# ------------------------------
st.set_page_config(
    page_title="VALORANT PROPS LAB",
    page_icon="🔫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Injection for Pro UI
st.markdown("""
<style>
    .stDataFrame {
        background-color: #0e1117 !important;
        border-radius: 10px !important;
    }
    .stButton>button {
        background: linear-gradient(90deg, #ff4d4d, #f9cb28) !important;
        border: none !important;
    }
    .stChatInput {
        bottom: 20px;
        position: fixed !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 8px 8px 0 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------
# SCRAPER MODULE
# ------------------------------
class ValorantDataScraper:
    def __init__(self):
        self.session = httpx.Client(
            headers={'User-Agent': UserAgent().random},
            timeout=30,
            follow_redirects=True
        )
        self.rate_limit = 3
        self.last_request = 0

    def _delay(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed + random.uniform(0.5, 1.5))
        self.last_request = time.time()

    def scrape_vlr_match(self, match_url):
        try:
            self._delay()
            response = self.session.get(match_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            players = []
            
            # Actual scraping logic for VLR.gg
            for team in soup.find_all('div', class_='vm-stats-game'):
                team_name = team.find('div', class_='team-name').text.strip()
                
                for player_row in team.find_all('tr')[1:]:
                    cols = player_row.find_all('td')
                    players.append({
                        'name': cols[0].find('div', class_='text-of').text.strip(),
                        'team': team_name,
                        'kills': float(cols[2].text.strip()),
                        'deaths': float(cols[3].text.strip()),
                        'acs': float(cols[8].text.strip()),
                        'map': 'Map 1'
                    })
            
            return pd.DataFrame(players)
            
        except Exception as e:
            st.error(f"Scraping failed: {str(e)}")
            return pd.DataFrame()

    def stealth_scrape(self, url):
        """When normal scraping fails"""
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        try:
            driver.get(url)
            time.sleep(5)  # Let JavaScript render
            soup = BeautifulSoup(driver.page_source, 'lxml')
            # Add parsing logic here
            return pd.DataFrame()
        finally:
            driver.quit()

# ------------------------------
# PREDICTION ENGINE
# ------------------------------
class PropsPredictor:
    def __init__(self):
        self.team_strength = {
            "Team Liquid Brazil": 1.14,
            "MIBR GC": 5.00
        }
        
        self.position_factors = {
            "Duelist": 1.15,
            "Initiator": 1.05,
            "Controller": 0.95,
            "Sentinel": 0.90,
            "Flex": 1.00
        }

    def calculate_predictions(self, players_df):
        predictions = []
        for _, row in players_df.iterrows():
            try:
                # Core calculation
                mu = row['line'] * self.position_factors.get(row['position'], 1.0)
                mu *= (1 + (1 - (self.team_strength[row['opponent']] / self.team_strength[row['team']])) * 0.1
                
                sigma = {
                    "Duelist": 3.5,
                    "Initiator": 3.0,
                    "Controller": 2.5,
                    "Sentinel": 2.0,
                    "Flex": 3.0
                }.get(row['position'], 3.0)
                
                p_over = 1 - norm.cdf(row['line'], mu, sigma)
                edge = p_over - 0.5
                
                predictions.append({
                    "Player": row['name'],
                    "Team": row['team'],
                    "Position": row['position'],
                    "Line": row['line'],
                    "P(OVER)": p_over,
                    "Edge": edge,
                    "Confidence": min(3, max(1, int(abs(edge) * 10)) * "⭐",
                    "Mu": mu,
                    "Sigma": sigma
                })
                
            except Exception as e:
                st.warning(f"Error processing {row['name']}: {str(e)}")
                continue

        return pd.DataFrame(predictions)

# ------------------------------
# UI COMPONENTS
# ------------------------------
def render_kill_matrix(df):
    """Grid layout from your screenshot"""
    cols = st.columns(4)
    for idx, (_, row) in enumerate(df.iterrows()):
        with cols[idx % 4]:
            with st.container(border=True):
                st.markdown(f"""
                **{row['Player']}**  
                *{row['Team']} {row['Position']}*  
                ### {row['Line']}  
                📊 {row['P(OVER)']:.0%} | {row['Confidence']}
                """)
                
                fig = px.histogram(
                    x=np.random.normal(row['Mu'], row['Sigma'], 1000),
                    nbins=20,
                    range_x=[row['Mu']-3*row['Sigma'], row['Mu']+3*row['Sigma']]
                )
                fig.add_vline(x=row['Line'], line_dash="dash")
                st.plotly_chart(fig, use_container_width=True)

def props_lab_view(df):
    """Optimizer panel"""
    with st.expander("🔥 PROPS LAB OPTIMIZER", expanded=True):
        st.dataframe(
            df.sort_values("Edge", ascending=False),
            column_config={
                "P(OVER)": st.column_config.ProgressColumn(
                    format="%.0f%%",
                    min_value=0,
                    max_value=1
                ),
                "Edge": st.column_config.NumberColumn(
                    format="+%.2f",
                    help="Expected value edge"
                )
            },
            hide_index=True,
            use_container_width=True
        )

# ------------------------------
# MAIN APP
# ------------------------------
def main():
    # Initialize services
    scraper = ValorantDataScraper()
    predictor = PropsPredictor()
    
    # Session state
    if 'predictions' not in st.session_state:
        st.session_state.predictions = pd.DataFrame()
    
    # Header
    st.title("VALORANT PROPS LAB")
    st.subheader("Game Changers • Match Analysis")
    
    # Data loading
    with st.sidebar:
        st.header("Data Sources")
        match_url = st.text_input("VLR.gg Match URL")
        if st.button("Scrape Live Data"):
            with st.spinner("Fetching match data..."):
                match_data = scraper.scrape_vlr_match(match_url)
                if not match_data.empty:
                    st.session_state.predictions = predictor.calculate_predictions(match_data)
                    st.success("Data loaded!")
    
    # Main interface
    tab1, tab2 = st.tabs(["📊 Player Matrix", "🔍 Props Lab"])
    
    with tab1:
        if not st.session_state.predictions.empty:
            render_kill_matrix(st.session_state.predictions)
        else:
            st.warning("Load match data to begin")
    
    with tab2:
        if not st.session_state.predictions.empty:
            props_lab_view(st.session_state.predictions)
        else:
            st.info("Scrape a match to analyze props")

if __name__ == "__main__":
    main()
