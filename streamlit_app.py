# streamlit_app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from scipy.stats import norm
import logging

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(
    page_title="VALORANT GC Match Analyst",
    page_icon="🔫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# Logging
# ------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Session State
# ------------------------------
if 'predictions' not in st.session_state:
    st.session_state.predictions = pd.DataFrame()
if 'match_history' not in st.session_state:
    st.session_state.match_history = pd.DataFrame()
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# ------------------------------
# Preloaded Match Data
# ------------------------------
def load_default_match():
    players = [
        # MIBR GC Players
        {"name": "Mel", "team": "MIBR GC", "line": 38.5, "position": "Duelist"},
        {"name": "Bizerra", "team": "MIBR GC", "line": 47.5, "position": "Initiator"},
        {"name": "lissa", "team": "MIBR GC", "line": 36.0, "position": "Controller"},
        {"name": "srN", "team": "MIBR GC", "line": 48.5, "position": "Sentinel"},
        {"name": "bstrdd", "team": "MIBR GC", "line": 47.0, "position": "Flex"},
        
        # Team Liquid Brazil Players
        {"name": "Jelly", "team": "Team Liquid Brazil", "line": 55.5, "position": "Duelist"},
        {"name": "Joojina", "team": "Team Liquid Brazil", "line": 43.5, "position": "Initiator"},
        {"name": "sayuri", "team": "Team Liquid Brazil", "line": 32.5, "position": "Controller"},
        {"name": "isaa", "team": "Team Liquid Brazil", "line": 41.5, "position": "Sentinel"},
        {"name": "daiki", "team": "Team Liquid Brazil", "line": 46.5, "position": "Flex"},
    ]
    
    for player in players:
        player.update({
            "opponent": "Team Liquid Brazil" if player["team"] == "MIBR GC" else "MIBR GC",
            "event": "VALORANT Game Changers",
            "added_at": datetime.now(timezone.utc),
            "map_count": 3  # Best of 5 but lines are for first 3 maps
        })
    
    return pd.DataFrame(players)

# ------------------------------
# Prediction Model
# ------------------------------
def calculate_predictions(players_df, match_history_df):
    if players_df.empty:
        return pd.DataFrame()

    # Team strength adjustment based on odds
    team_strength = {
        "Team Liquid Brazil": 1.14,
        "MIBR GC": 5.00
    }
    
    predictions = []
    for _, row in players_df.iterrows():
        try:
            # Base parameters
            base_line = row['line']
            position = row.get('position', 'Flex')
            
            # Position adjustments
            position_factors = {
                "Duelist": 1.15,
                "Initiator": 1.05,
                "Controller": 0.95,
                "Sentinel": 0.90,
                "Flex": 1.00
            }
            
            # Opponent strength adjustment
            opponent_factor = team_strength[row['opponent']] / team_strength[row['team']]
            
            # Calculate adjusted mean
            mu = base_line * position_factors.get(position, 1.0) * (1 + (1 - opponent_factor) * 0.1)
            
            # Dynamic sigma based on position and opponent
            sigma = {
                "Duelist": 3.5,
                "Initiator": 3.0,
                "Controller": 2.5,
                "Sentinel": 2.0,
                "Flex": 3.0
            }.get(position, 3.0) * (1 + (opponent_factor - 1) * 0.2)
            
            # Calculate probability
            p_over = 1 - norm.cdf(base_line, mu, sigma)
            
            # Confidence calculation
            confidence_score = abs(p_over - 0.5) * 2
            confidence = (
                "⭐⭐⭐" if confidence_score > 0.3 else
                "⭐⭐" if confidence_score > 0.15 else
                "⭐"
            )
            
            # Add historical data if available
            historical_avg = ""
            if not match_history_df.empty and row['name'] in match_history_df['name'].values:
                hist_data = match_history_df[match_history_df['name'] == row['name']]
                historical_avg = f"\n📊 Hist. Avg: {hist_data['kills'].mean():.1f} (±{hist_data['kills'].std():.1f})"
            
            predictions.append({
                "Player": row['name'],
                "Team": row['team'],
                "Position": position,
                "Opponent": row['opponent'],
                "Line": base_line,
                "P(OVER)": f"{p_over:.0%}",
                "Verdict": "✅ OVER" if p_over > 0.55 else "❌ UNDER",
                "Confidence": confidence,
                "Details": f"μ={mu:.1f}, σ={sigma:.1f}{historical_avg}"
            })

        except Exception as e:
            logger.warning(f"Prediction error for {row['name']}: {e}")
            continue

    return pd.DataFrame(predictions)

# ------------------------------
# Enhanced Analyst Bot
# ------------------------------
class EsportsAnalyst:
    def __init__(self):
        self.knowledge_base = {
            "model": "Our model considers:\n"
                    "- Player position (Duelists expected to frag more)\n"
                    "- Team strength (TLB favored 1.14 vs MIBR 5.00)\n"
                    "- Normal distribution around adjusted mean\n\n"
                    "Duelists get +15% expectation, Controllers -5%",
            "confidence": "Confidence stars:\n"
                        "⭐ = 50-65% certainty\n"
                        "⭐⭐ = 65-80%\n"
                        "⭐⭐⭐ = 80%+",
            "matchup": "TLB vs MIBR GC Key Factors:\n"
                      "- Team Liquid Brazil heavily favored (1.14 odds)\n"
                      "- Best of 5 but lines are for first 3 maps\n"
                      "- Expect TLB players to hit OVER more consistently",
            "help": "Ask me about:\n"
                   "- Specific player predictions\n"
                   "- Team matchup analysis\n"
                   "- How our model works\n"
                   "- Confidence explanations\n"
                   "- Historical performance (if data loaded)"
        }

    def generate_response(self, question, preds_df, match_history_df):
        question = question.lower().strip()
        
        # Check knowledge base first
        for key in self.knowledge_base:
            if key in question:
                return self.knowledge_base[key]
        
        # Player-specific queries
        if not preds_df.empty:
            player_query = next((name for name in preds_df['Player'].unique() if name.lower() in question), None)
            if player_query:
                player_data = preds_df[preds_df['Player'] == player_query].iloc[0]
                response = [
                    f"**{player_query} Prediction** ({player_data['Team']} {player_data['Position']})",
                    f"Line: {player_data['Line']} kills",
                    f"Verdict: {player_data['Verdict']} ({player_data['P(OVER)']})",
                    f"Confidence: {player_data['Confidence']}",
                    f"Model Details: {player_data['Details']}"
                ]
                
                # Add historical data if available
                if not match_history_df.empty and player_query in match_history_df['name'].values:
                    hist = match_history_df[match_history_df['name'] == player_query]
                    response.append(f"\n**Last {len(hist)} matches**: Avg {hist['kills'].mean():.1f} kills")
                
                return "\n".join(response)
        
        # Team analysis
        if any(team in question for team in ["tl", "tl brazil", "team liquid"]):
            return (
                "**Team Liquid Brazil Analysis**:\n"
                "- Heavy favorites (1.14 odds)\n"
                "- Expect consistent performance across maps\n"
                "- Jelly (Duelist) has highest line at 55.5\n"
                "- Team likely to control pace of match"
            )
        
        if any(team in question for team in ["mibr", "mibr gc"]):
            return (
                "**MIBR GC Analysis**:\n"
                "- Underdogs (5.00 odds)\n"
                "- May struggle against TLB's coordination\n"
                "- srN (Sentinel) has highest line at 48.5\n"
                "- Need standout performances to compete"
            )
        
        return (
            "I'm not sure I understand. Try asking about:\n"
            "- Specific players (Mel, Jelly, etc.)\n"
            "- Team Liquid Brazil or MIBR GC analysis\n"
            "- How the model works\n"
            "- Confidence explanations"
        )

# ------------------------------
# Match History Upload
# ------------------------------
def handle_history_upload():
    uploaded_file = st.sidebar.file_uploader("Upload Match History CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            required_cols = {"name", "kills", "team", "opponent"}
            if required_cols.issubset(df.columns):
                st.session_state.match_history = df
                st.sidebar.success("Match history loaded successfully!")
            else:
                st.sidebar.error("CSV missing required columns (name, kills, team, opponent)")
        except Exception as e:
            st.sidebar.error(f"Error loading file: {e}")

# ------------------------------
# Main App
# ------------------------------
def main():
    # Header
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Valorant_logo_-_pink_color_version.svg/1200px-Valorant_logo_-_pink_color_version.svg.png", 
             width=150)
    st.title("VALORANT GC Match Analyst")
    st.subheader("Team Liquid Brazil vs MIBR GC • 2:00PM PDT • Best of 5")
    
    # Initialize default data
    if st.session_state.predictions.empty:
        st.session_state.predictions = calculate_predictions(
            load_default_match(),
            st.session_state.match_history
        )

    # Main columns
    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        # Match Predictions Display
        with st.expander("📊 Current Predictions", expanded=True):
            st.dataframe(
                st.session_state.predictions.sort_values("P(OVER)", ascending=False),
                column_config={
                    "P(OVER)": st.column_config.ProgressColumn(
                        "Probability",
                        format="%.0f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Details": st.column_config.TextColumn(
                        "Model Details",
                        help="μ = adjusted mean, σ = standard deviation"
                    ),
                    "Verdict": st.column_config.TextColumn(
                        "Recommendation",
                        help="Our model's suggested bet"
                    )
                },
                hide_index=True,
                use_container_width=True,
                height=600
            )
            
            st.caption("Note: Lines are for kills across first 3 maps")

        # Match History Upload
        handle_history_upload()

    with col2:
        # Chat interface
        st.subheader("💬 Match Analyst")
        
        # Display chat history
        chat_container = st.container(height=500)
        with chat_container:
            for chat in st.session_state.chat_history:
                if chat['role'] == "user":
                    st.chat_message("user").markdown(chat['content'])
                else:
                    st.chat_message("assistant").markdown(chat['content'])
        
        # Chat input
        if question := st.chat_input("Ask about the match..."):
            st.session_state.chat_history.append({"role": "user", "content": question})
            
            analyst = EsportsAnalyst()
            with st.spinner("Analyzing..."):
                response = analyst.generate_response(
                    question,
                    st.session_state.predictions,
                    st.session_state.match_history
                )
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

if __name__ == "__main__":
    main()
