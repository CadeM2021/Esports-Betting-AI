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
                
                # Sample parsing - replace with actual site structure
                team1 = {"name": "Team A", "players": []}
                team2 = {"name": "Team B", "players": []}
                
                # Add sample players (replace with actual scraping)
                match_data.add_player("Player1", team1["name"], "Duelist", 25.5, team2["name"])
                match_data.add_player("Player2", team1["name"], "Initiator", 22.0, team2["name"])
                match_data.add_player("Player3", team2["name"], "Duelist", 27.5, team1["name"])
                match_data.add_player("Player4", team2["name"], "Sentinel", 19.5, team1["name"])
                
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
        "Team A": 1.25,
        "Team B": 3.50,
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
                strength_ratio = opponent_strength / team_strength
                mu = row["line"] * position_mod * (1 + (1 - strength_ratio) * 0.1)
                
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
        .player-card {
            border: 1px solid #2E4053;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }
    </style>
    """, unsafe_allow_html=True)

def render_player_card(player):
    with st.container():
        st.markdown(f"""
        <div class="player-card">
            <h3>{player['Player']}</h3>
            <p><b>{player['Team']}</b> | {player['Position']}</p>
            <h2>{player['Line']:.1f} Kills</h2>
            <p>Probability: <b>{player['P(OVER)']:.0%}</b> | Confidence: {player['Confidence']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Kill distribution chart
        x = np.linspace(player['μ']-3*player['σ'], player['μ']+3*player['σ'], 100)
        y = norm.pdf(x, player['μ'], player['σ'])
        fig = px.area(x=x, y=y)
        fig.add_vline(x=player['Line'], line_dash="dash")
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

def render_player_matrix(df):
    if df.empty:
        st.warning("No player data available")
        return
        
    cols = st.columns(4)
    for idx, (_, row) in enumerate(df.iterrows()):
        with cols[idx % 4]:
            render_player_card(row)

def render_props_lab(df):
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
    
    # Session state
    if "predictions" not in st.session_state:
        st.session_state.predictions = pd.DataFrame()
    
    # Sidebar controls
    with st.sidebar:
        st.title("Data Sources")
        match_url = st.text_input(
            "VLR.gg Match URL",
            placeholder="https://www.vlr.gg/12345/team1-vs-team2"
        )
        
        if st.button("Load Sample Data", type="primary"):
            sample_data = MatchData()
            sample_data.add_player("T3XTURE", "Gen.G", "Duelist", 35.5, "DRX")
            sample_data.add_player("PlayerJF", "Team A", "Initiator", 28.5, "Team B")
            sample_data.add_player("TYDIAN", "Team B", "Duelist", 24.5, "Team A")
            st.session_state.predictions = predictor.calculate_predictions(sample_data.get_dataframe())
            st.success("Sample data loaded!")
    
    # Main interface
    st.title("VALORANT PROPS LAB")
    st.caption("Advanced betting analytics for VALORANT esports")
    
    tab1, tab2 = st.tabs(["📊 Player Matrix", "🔍 Props Lab"])
    
    with tab1:
        render_player_matrix(st.session_state.predictions)
    
    with tab2:
        render_props_lab(st.session_state.predictions)

if __name__ == "__main__":
    main()
