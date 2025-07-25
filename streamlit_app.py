# valorant_props_lab.py
import streamlit as st
import pandas as pd
import numpy as np
import json
from scipy.stats import norm
import plotly.express as px

# ------------------------------
# CONFIGURATION
# ------------------------------
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
            "opponent": opponent
        })
        
    def get_dataframe(self):
        return pd.DataFrame(self.players)

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
    
    def calculate_predictions(self, raw_data):
        if raw_data.empty:
            return pd.DataFrame()
            
        predictions = []
        
        for _, row in raw_data.iterrows():
            try:
                # Simplified calculation for demo
                position_mod = self.POSITION_MODIFIERS.get(row.get("position", "Flex"), 1.0)
                mu = row["line"] * position_mod
                sigma = 3.0  # Fixed for simplicity
                
                p_over = 1 - norm.cdf(row["line"], mu, sigma)
                edge = p_over - 0.5
                confidence = min(3, max(1, int(abs(edge) * 10)))
                
                predictions.append({
                    "Player": row["name"],
                    "Team": row["team"],
                    "Position": row.get("position", "Flex"),
                    "Line": row["line"],
                    "P(OVER)": p_over,
                    "Edge": edge,
                    "Confidence": "⭐" * confidence,
                    "μ": mu,
                    "σ": sigma
                })
                
            except Exception as e:
                st.warning(f"Error processing {row.get('name', 'Unknown')}: {str(e)}")
                continue
                
        return pd.DataFrame(predictions)

# ------------------------------
# UI COMPONENTS
# ------------------------------
def setup_ui():
    st.markdown("""
    <style>
        .stDataFrame {
            border-radius: 10px !important;
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
            use_container_width=True
        )

# ------------------------------
# DATA INPUT FUNCTIONS
# ------------------------------
def load_underdog_lines():
    st.sidebar.subheader("Underdog Lines Input")
    
    # Text area for JSON input
    json_input = st.sidebar.text_area(
        "Paste Underdog Lines JSON",
        height=200,
        help="Paste player props data from Underdog in JSON format"
    )
    
    if st.sidebar.button("Process Underdog Data"):
        if json_input:
            try:
                data = json.loads(json_input)
                match_data = MatchData()
                
                # Example parsing - adapt to actual Underdog JSON structure
                for player in data.get('players', []):
                    match_data.add_player(
                        name=player.get('name', 'Unknown'),
                        team=player.get('team', 'Unknown'),
                        position=player.get('position', 'Flex'),
                        line=float(player.get('line', 0)),
                        opponent=player.get('opponent', 'Unknown')
                    )
                
                predictor = PropsPredictor()
                st.session_state.predictions = predictor.calculate_predictions(match_data.get_dataframe())
                st.sidebar.success("Underdog data processed!")
                
            except Exception as e:
                st.sidebar.error(f"Error parsing JSON: {str(e)}")
        else:
            st.sidebar.warning("Please paste Underdog JSON data")

def load_sample_data():
    if st.sidebar.button("Load Sample Data"):
        sample_data = MatchData()
        sample_data.add_player("T3XTURE", "Gen.G", "Duelist", 35.5, "DRX")
        sample_data.add_player("PlayerJF", "Team A", "Initiator", 28.5, "Team B")
        sample_data.add_player("TYDIAN", "Team B", "Duelist", 24.5, "Team A")
        
        predictor = PropsPredictor()
        st.session_state.predictions = predictor.calculate_predictions(sample_data.get_dataframe())
        st.sidebar.success("Sample data loaded!")

# ------------------------------
# MAIN APPLICATION
# ------------------------------
def main():
    setup_ui()
    
    # Initialize session state
    if "predictions" not in st.session_state:
        st.session_state.predictions = pd.DataFrame()
    
    # Sidebar controls
    st.sidebar.title("Data Input")
    load_underdog_lines()
    load_sample_data()
    
    # Main interface
    st.title("VALORANT PROPS LAB")
    
    tab1, tab2 = st.tabs(["📊 Player Matrix", "🔍 Props Lab"])
    
    with tab1:
        render_player_matrix(st.session_state.predictions)
    
    with tab2:
        render_props_lab(st.session_state.predictions)

if __name__ == "__main__":
    main()
