import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# ======================
# 1. SCRAPING FUNCTIONS (Pure requests + BS4)
# ======================
def scrape_underdog_lines():
    """Scrape player kill lines (static content only)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(
            "https://underdogfantasy.com/pick-em/higher-lower",
            headers=headers,
            timeout=10
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        
        players = []
        for elem in soup.select('div.player-line')[:15]:  # Limit to 15 players
            try:
                name = elem.select_one('div.player-name').text.strip()
                line = float(elem.select_one('div.line-value').text.strip())
                players.append({"name": name, "line": line})
            except Exception as e:
                st.warning(f"Failed to parse player: {str(e)}")
                continue
                
        return pd.DataFrame(players) if players else pd.DataFrame({"name": [], "line": []})
        
    except Exception as e:
        st.error(f"Underdog scraping failed (static only): {str(e)}")
        return pd.DataFrame({"name": [], "line": []})

def scrape_vlr_stats():
    """Scrape recent match stats from VLR.gg"""
    try:
        response = requests.get("https://www.vlr.gg/matches", timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        stats = []
        for match in soup.select("div.wf-card.mod-match"):
            for player in match.select("div.player"):
                try:
                    name = player.select_one("div.player-name").text.strip()
                    kills = int(player.select_one("span.mod-kills").text)
                    stats.append({"name": name, "kills": kills})
                except:
                    continue
                    
        return pd.DataFrame(stats) if stats else pd.DataFrame({"name": [], "kills": []})
        
    except Exception as e:
        st.error(f"VLR.gg scraping failed: {str(e)}")
        return pd.DataFrame({"name": [], "kills": []})

# ======================
# 2. STREAMLIT APP
# ======================
st.title("🔫 Valorant Player Kill Dashboard")

@st.cache_data(ttl=3600)
def load_data():
    with st.spinner("📡 Loading live data..."):
        lines_df = scrape_underdog_lines()
        stats_df = scrape_vlr_stats()
        
        if lines_df.empty or stats_df.empty:
            st.warning("Using sample data due to scraping limitations")
            return pd.DataFrame({
                "name": ["PlayerA", "PlayerB"],
                "line": [22.5, 18.5],
                "mean": [23.1, 19.2],
                "count": [5, 5],
                "edge": [0.6, 0.7]
            })
        
        merged = pd.merge(
            lines_df, 
            stats_df.groupby("name")["kills"].agg(["mean", "count"]).reset_index(),
            on="name", 
            how="left"
        ).dropna()
        merged["edge"] = merged["mean"] - merged["line"]
        return merged.sort_values("edge", ascending=False)

# ======================
# 3. UI RENDERING
# ======================
df = load_data()

if not df.empty:
    st.dataframe(
        df.style
        .bar(subset=["edge"], align="mid", color=["#FF6B6B", "#4ECDC4"])
        .highlight_max(subset=["edge"], color="lightgreen")
        .format({"mean": "{:.1f}", "edge": "{:.1f}"}),
        height=600,
        use_container_width=True
    )
    
    col1, col2 = st.columns(2)
    with col1:
        min_edge = st.slider("Minimum Edge", -5.0, 10.0, 1.0)
    with col2:
        min_matches = st.slider("Minimum Matches", 1, 20, 5)
    
    filtered = df[(df["edge"] >= min_edge) & (df["count"] >= min_matches)]
    st.metric("Value Bets Found", len(filtered))
else:
    st.error("No data available - check if scraping is blocked")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.caption(f"Last update: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
