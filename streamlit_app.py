import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

# ======================
# 1. CORE FUNCTIONS (NEW)
# ======================
def scrape_player_stats(player_id):
    """Scrape VLR.gg for player stats (mock data for now)"""
    try:
        # TODO: Replace with real scraping
        mock_kills = {
            3187: [24, 19, 27, 22, 18],  # Example: Cryo's stats
            1234: [21, 20, 23, 19, 25]   # Example: Player 2
        }
        return {"kills": mock_kills.get(player_id, [20, 21, 22])}
    except Exception as e:
        st.error(f"⚠️ Scraping failed: {e}")
        return {"kills": [20, 21, 22]}  # Fallback data

def log_bet(player_name, predicted, actual, bet_type):
    """Record bets to history.csv"""
    try:
        with open('history.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                player_name,
                predicted,
                actual,
                bet_type,
                "WIN" if (bet_type == "OVER" and actual > predicted) or 
                         (bet_type == "UNDER" and actual < predicted) else "LOSE"
            ])
        st.success("✅ Bet logged!")
    except Exception as e:
        st.error(f"Failed to log bet: {e}")

# ======================
# 2. STREAMLIT UI (YOUR WORKING VERSION + UPGRADES)
# ======================
st.title("🎯 Valorant Kill Line Predictor")
st.markdown("Compare player kill predictions vs. DFS lines")

# --- Input Section ---
col1, col2 = st.columns(2)
with col1:
    player_name = st.text_input("🔍 Enter Player Name (e.g., 'Cryo'):")
with col2:
    player_id = st.number_input("🆔 VLR.gg Player ID", min_value=1, value=3187)

book_line = st.number_input("📊 Enter Underdog Line (e.g., 22.5):", min_value=0.0, step=0.5)

# --- Toggle for New Features ---
use_new_features = st.toggle("🔴 Enable Experimental Features", False)

if player_name and book_line:
    if use_new_features:
        # NEW VERSION WITH SCRAPING
        stats = scrape_player_stats(player_id)
        avg_kills = sum(stats["kills"]) / len(stats["kills"])
        
        st.subheader(f"Last {len(stats['kills'])} Matches")
        st.dataframe(pd.DataFrame({"Kills": stats["kills"], "Map": ["Ascent", "Haven", "Split", "Bind", "Icebox"][:len(stats["kills"])]}))
        
        edge = avg_kills - book_line
        bet_type = "OVER" if edge > 1.5 else "UNDER" if edge < -1.5 else None
        
        if bet_type:
            if st.button(f"💰 Bet {bet_type}"):
                log_bet(player_name, avg_kills, book_line, bet_type)
    else:
        # ORIGINAL WORKING VERSION
        dummy_data = {
            "Match": ["GX vs BBL", "GX vs NAVI", "GX vs FUT"],
            "Kills": [24, 19, 27],
            "Map": ["Ascent", "Haven", "Split"]
        }
        df = pd.DataFrame(dummy_data)
        st.dataframe(df)
        avg_kills = df["Kills"].mean()
        st.metric("Predicted Kills", f"{avg_kills:.1f}")

# --- Bet History ---
if st.checkbox("📜 View Bet History"):
    try:
        history = pd.read_csv("history.csv")
        st.dataframe(history)
    except FileNotFoundError:
        st.warning("No bet history yet")

# --- Next Steps ---
st.markdown("""
---
### 🚀 Next Steps:
1. **Replace mock data** with real VLR.gg scraping
2. **Auto-fetch Underdog lines** (Selenium/API)
3. **Improve hit rate tracking**
""")
