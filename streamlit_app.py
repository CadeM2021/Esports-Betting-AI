# valorant_props_lab.py
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

# ------------------------------
# CONFIGURATION
# ------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="VALORANT PROPS LAB",
    page_icon="🔫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# DATA MODEL
# ------------------------------
class MatchData:
    def __init__(self):
        self.players = []
        self.teams = {}
        
    def add_player(self, name, team, position, line, opponent):
        self.players.append({
            "name": name,
            "team": team,
            "position": position,
            "line": line,
            "opponent": opponent,
            "timestamp": datetime.now(timezone.utc)
        })
        
    def get_dataframe(self):
        return pd.DataFrame(self.players)

# ------------------------------
# SCRAPER SERVICE
# ------------------------------
class ValorantScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": UserAgent().random,
            "Accept-Language": "en-US,en;q=0.9"
        }
        self.min_delay = 2.5
        self.max_delay = 5.0
        
    def _random_delay(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))
        
    def scrape_vlr_match(self, match_url):
        try:
            self._random_delay()
            
            with httpx.Client() as client:
                response = client.get(
                    match_url,
                    headers=self.headers,
                    timeout=30.0,
                    follow_redirects=True
                )
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                match_data = MatchData()
                
                # Sample parsing logic - adapt to actual site structure
                for team_div in soup.find_all("div", class_="team-container"):
                    team_name = team_div.find("div", class_="team-name").text.strip()
                    
                    for player_div in team_div.find_all("div", class_="player"):
                        name = player_div.find("span", class_="name").text.strip()
                        position = player_div.find("span", class_="role").text.strip()
                        kills = float(player_div.find("span", class_="kills").text)
                        
                        match_data.add_player(
                            name=name,
                            team=team_name,
                            position=position,
                            line=kills,
                            opponent="Opponent Team"  # Replace with actual logic
                        )
                
                return match_data.get_dataframe()
                
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}")
            return pd.DataFrame()

# ------------------------------
# PREDICTION ENGINE
# ------------------------------
class PropsPredictor:
    POSITION_MODIFIERS = {
        "Duelist": 1.15,
        "Initiator": 1.05,
        "Controller": 0.95,
        "Sentinel": 0.90,
        "Flex": 1.00
    }
    
    TEAM_STRENGTH = {
        "Team Liquid Brazil": 1.14,
        "MIBR GC": 5.00,
        "Default": 1.00
    }
    
    def calculate_predictions(self, raw_data):
        if raw_data.empty:
            return pd.DataFrame()
            
        predictions = []
        
        for _, row in raw_data.iterrows():
            try:
                # Calculate adjusted mean
                team_strength = self.TEAM_STRENGTH.get(row["team"], self.TEAM_STRENGTH["Default"])
                opponent_strength = self.TEAM_STRENGTH.get(row["opponent"], self.TEAM_STRENGTH["Default"])
                
                position_mod = self.POSITION_MODIFIERS.get(row.get("position", "Flex"), 1.0)
                mu = row["line"] * position_mod * (1 + (1 - (opponent_strength / team_strength)) * 0.1
                
                # Dynamic standard deviation
                sigma = {
                    "Duelist": 3.5,
                    "Initiator": 3.0,
                    "Controller": 2.5,
                    "Sentinel": 2.0
                }.get(row.get("position", "Flex"), 3.0)
                
                # Probability calculations
                line = row["line"]
                p_over = 1 - norm.cdf(line, mu, sigma)
                edge = p_over - 0.5
                confidence = min(3, max(1, int(abs(edge) * 10)))
                
                predictions.append({
                    "Player": row["name"],
                    "Team": row["team"],
                    "Position": row.get("position", "Flex"),
                    "Line": line,
                    "P(OVER)": p_over,
                    "Edge": edge,
                    "Confidence": "⭐" * confidence,
                    "μ": mu,
                    "σ": sigma
                })
                
            except Exception as e:
                logger.warning(f"Prediction error for {row.get('name', 'Unknown')}: {str(e)}")
                continue
                
        return pd.DataFrame(predictions)

# ------------------------------
# UI COMPONENTS
# ------------------------------
def setup_ui():
    """Configure custom Streamlit styles"""
    st.markdown("""
    <style>
        .stDataFrame {
            background-color: #0E1117 !important;
            border-radius: 10px !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 16px;
            border-radius: 8px 8px 0 0 !important;
        }
        .stButton>button {
            background: linear-gradient(90deg, #FF4D4D, #F9CB28);
            color: white !important;
            border: none !important;
        }
        .stAlert [data-testid="stMarkdownContainer"] {
            font-size: 1.1rem;
        }
    </style>
    """, unsafe_allow_html=True)

def render_player_matrix(df):
    """Grid layout showing player cards"""
    if df.empty:
        st.warning("No player data available")
        return
        
    cols = st.columns(4)
    for idx, (_, row) in enumerate(df.iterrows()):
        with cols[idx % 4]:
            with st.container(border=True):
                st.markdown(f"""
                **{row['Player']}**  
                *{row['Team']} {row['Position']}*  
                ### {row['Line']:.1f}  
                📊 {row['P(OVER)']:.0%} | {row['Confidence']}
                """)
                
                # Kill distribution visualization
                x = np.linspace(row['μ']-3*row['σ'], row['μ']+3*row['σ'], 100)
                y = norm.pdf(x, row['μ'], row['σ'])
                fig = px.area(x=x, y=y)
                fig.add_vline(x=row['Line'], line_dash="dash")
                fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)

def render_props_lab(df):
    """Optimization dashboard"""
    if df.empty:
        st.info("Load match data to analyze props")
        return
        
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
                    help="Expected value edge over market"
                ),
                "Line": st.column_config.NumberColumn(
                    format="%.1f",
                    help="Kills line set by sportsbook"
                )
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )

# ------------------------------
# MAIN APPLICATION
# ------------------------------
def main():
    setup_ui()
    
    # Initialize services
    scraper = ValorantScraper()
    predictor = PropsPredictor()
    
    # Session state management
    if "predictions" not in st.session_state:
        st.session_state.predictions = pd.DataFrame()
    
    # Sidebar controls
    with st.sidebar:
        st.title("Data Sources")
        match_url = st.text_input(
            "VLR.gg Match URL",
            placeholder="https://www.vlr.gg/12345/team1-vs-team2"
        )
        
        if st.button("Scrape Match Data", type="primary"):
            with st.spinner("Fetching live match data..."):
                raw_data = scraper.scrape_vlr_match(match_url)
                if not raw_data.empty:
                    st.session_state.predictions = predictor.calculate_predictions(raw_data)
                    st.success("Data loaded successfully!")
                else:
                    st.error("Failed to load match data")
    
    # Main interface
    st.title("VALORANT PROPS LAB")
    st.caption("Advanced analytics for VALORANT Game Changers matches")
    
    tab1, tab2 = st.tabs(["📊 Player Matrix", "🔍 Props Lab"])
    
    with tab1:
        render_player_matrix(st.session_state.predictions)
    
    with tab2:
        render_props_lab(st.session_state.predictions)

if __name__ == "__main__":
    main()
