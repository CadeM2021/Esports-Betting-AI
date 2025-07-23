import streamlit as st
import pandas as pd
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import time

# ======================
# 1. SCRAPING FUNCTIONS (Selenium-free)
# ======================
def scrape_underdog_lines():
    """Scrape player kill lines using requests-html"""
    session = HTMLSession()
    try:
        r = session.get("https://underdogfantasy.com/pick-em/higher-lower", timeout=20)
        r.html.render(sleep=5, timeout=20)  # JavaScript rendering
        
        players = []
        for elem in r.html.find('div.player-line', first=15):
            try:
                name = elem.find('div.player-name', first=True).text
                line = float(elem.find('div.line-value', first=True).text)
                players.append({"name": name, "line": line})
            except Exception as e:
                st.warning(f"Failed to parse player: {str(e)}")
                continue
                
        return pd.DataFrame(players) if players else pd.DataFrame({"name": [], "line": []})
        
    except Exception as e:
        st.error(f"Underdog scraping failed: {str(e)}")
        return pd.DataFrame({"name": [], "line": []})

def scrape_vlr_stats():
    """Scrape recent match stats from VLR.gg"""
    try:
        session = HTMLSession()
        r = session.get("https://www.vlr.gg/matches", timeout=10)
        
        stats = []
        for match in r.html.find('div.wf-card.mod-match'):
            for player in match.find('div.player'):
                try:
                    name = player.find('div.player-name', first=True).text.strip()
                    kills = int(player.find('span.mod-kills', first=True).text)
                    stats.append({"name": name, "kills": kills})
                except:
                    continue
                    
        return pd.DataFrame(stats) if stats else pd.DataFrame({"name": [], "kills": []})
        
    except Exception as e:
        st.error(f"VLR.gg scraping failed: {str(e)}")
        return pd.DataFrame({"name": [], "kills": []})

# ======================
# 2. STREAMLIT APP (Optimized)
# ======================
st.title("🔫 Valorant Player Kill Dashboard")

@st.cache_data(ttl=3600)
def load_data():
    with st.spinner("📡 Loading live data..."):
        lines_df = scrape_underdog_lines()
        stats_df = scrape_vlr_stats()
        
        if lines_df.empty or stats_df.empty:
            st.warning("Using sample data due to scraping issues")
            return pd.DataFrame({
                "name": ["Sample1", "Sample2"],
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
    # Display dataframe with styling
    st.dataframe(
        df.style
        .bar(subset=["edge"], align="mid", color=["#FF6B6B", "#4ECDC4"])
        .highlight_max(subset=["edge"], color="lightgreen")
        .format({"mean": "{:.1f}", "edge": "{:.1f}"}),
        height=600,
        use_container_width=True
    )
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        min_edge = st.slider("Minimum Edge", -5.0, 10.0, 1.0)
    with col2:
        min_matches = st.slider("Minimum Matches", 1, 20, 5)
    
    filtered = df[(df["edge"] >= min_edge) & (df["count"] >= min_matches)]
    st.metric("Value Bets Found", len(filtered))
else:
    st.error("No data available - please try again later")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.caption(f"Last update: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
