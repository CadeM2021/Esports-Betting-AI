import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup  # Fixed typo (lib4 → bs4)

# Title
st.title("🎯 Valorant Kill Line Predictor")
st.markdown("Compare player kill predictions vs. DFS lines (PrizePicks/Underdog)")

# Input: Player Name
player_name = st.text_input("🔍 Enter Player Name (e.g., 'Cryo'):")

# Input: Underdog Line (manual for now)
book_line = st.number_input("📊 Enter Underdog Line (e.g., 22.5):", min_value=0.0, step=0.5)

if player_name and book_line:
    # --- Scrape VLR.gg (Dummy Example) ---
    st.subheader(f"Last 5 Matches for {player_name}")
    
    # Example dummy data (replace with real VLR.gg scrape later)
    dummy_data = {
        "Match": ["GX vs BBL", "GX vs NAVI", "GX vs FUT", "GX vs TL", "GX vs KC"],
        "Kills": [24, 19, 27, 22, 18],
        "Map": ["Ascent", "Haven", "Split", "Bind", "Icebox"]
    }
    df = pd.DataFrame(dummy_data)
    
    # Show table
    st.dataframe(df)

    # --- Calculate Prediction ---
    avg_kills = df["Kills"].mean()
    hit_rate = (df["Kills"] > book_line).mean() * 100  # % of time player beat the line

    # --- Display Results ---
    st.subheader("📊 Prediction vs. Line")
    col1, col2, col3 = st.columns(3)
    col1.metric("Predicted Kills", f"{avg_kills:.1f}")
    col2.metric("Underdog Line", f"{book_line:.1f}")
    col3.metric("Hit Rate", f"{hit_rate:.0f}%")

    # --- Bet Recommendation ---
    edge = avg_kills - book_line
    if edge > 1.5:
        st.success(f"✅ BET OVER (Edge: +{edge:.1f})")
    elif edge < -1.5:
        st.error(f"✅ BET UNDER (Edge: {edge:.1f})")
    else:
        st.warning("🚫 NO BET (Edge too small)")

# --- How to Improve ---
st.markdown("""
---
### 🚀 Next Steps:
1. **Replace dummy data** with real VLR.gg scraping (I'll help you!).
2. **Auto-fetch Underdog lines** (Selenium/API).
3. **Track historical bets** to improve hit rate.
""")
from bs4 import BeautifulSoup
import requests

def scrape_player_stats(player_id):
    url = f"https://www.vlr.gg/player/{player_id}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Add parsing logic here
    return {"kills": [24, 19, 27, 22, 18]}  # Replace with real data
