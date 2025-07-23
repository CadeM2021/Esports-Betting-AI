import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ======================
# 1. CORE FUNCTIONALITY
# ======================

# Sample data fallback
SAMPLE_DATA = pd.DataFrame({
    "name": ["PlayerA", "PlayerB", "PlayerC"],
    "line": [18.5, 22.5, 20.0],
    "mean": [19.2, 23.1, 21.5],
    "count": [5, 5, 5],
    "edge": [0.7, 0.6, 1.5]
})

def safe_scrape(url, css_selector):
    """Universal safe scraping function with error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.select(css_selector)
    except Exception as e:
        st.warning(f"⚠️ Scraping {url.split('//')[1].split('/')[0]} failed: {str(e)}")
        return []

def get_live_data():
    """Get combined data from all sources with fallback"""
    try:
        # 1. Scrape betting lines
        lines = []
        players = safe_scrape("https://underdogfantasy.com/pick-em/higher-lower", "div.player-line")[:20]
        
        for player in players:
            try:
                lines.append({
                    "name": player.select_one("div.player-name").text.strip(),
                    "line": float(player.select_one("div.line-value").text.strip())
                })
            except:
                continue

        # 2. Scrape match stats
        stats = []
        matches = safe_scrape("https://www.vlr.gg/matches", "div.wf-card.mod-match")
        
        for match in matches[:10]:  # Limit to 10 matches
            try:
                stats.append({
                    "name": match.select_one("div.player-name").text.strip(),
                    "kills": int(match.select_one("span.mod-kills").text)
                })
            except:
                continue

        # 3. Merge and process data
        if lines and stats:
            lines_df = pd.DataFrame(lines)
            stats_df = pd.DataFrame(stats)
            
            # Calculate average kills per player
            stats_agg = stats_df.groupby("name")["kills"].agg(["mean", "count"]).reset_index()
            
            # Merge with betting lines
            merged = pd.merge(lines_df, stats_agg, on="name", how="left").dropna()
            merged["edge"] = merged["mean"] - merged["line"]
            return merged.sort_values("edge", ascending=False)
            
    except Exception as e:
        st.error(f"🚨 Data processing error: {str(e)}")

    return SAMPLE_DATA  # Fallback if anything fails

# ======================
# 2. STREAMLIT UI
# ======================

st.set_page_config(
    page_title="Valorant Predictor",
    page_icon="🔫",
    layout="wide"
)

# Title and description
st.title("🎯 Valorant Predictive Dashboard")
st.markdown("""
    *Identify value bets by comparing betting lines to player performance stats*
    """)

# Data loading with cache
@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    with st.spinner("📡 Connecting to data sources..."):
        return get_live_data()

df = load_data()

# Dashboard Metrics
st.subheader("Live Insights")
cols = st.columns(4)
cols[0].metric("Total Players", len(df))
cols[1].metric("Positive Edge", len(df[df["edge"] > 0]))
cols[2].metric("Avg Edge", f"{df['edge'].mean():.1f}")
cols[3].metric("Top Value", f"{df['edge'].max():.1f}")

# Filters
with st.expander("⚙️ Filter Options", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        edge_filter = st.slider(
            "Minimum Edge Value",
            min_value=-2.0,
            max_value=5.0,
            value=0.5,
            step=0.1
        )
    with col2:
        matches_filter = st.slider(
            "Minimum Matches Tracked",
            min_value=1,
            max_value=20,
            value=3
        )

# Apply filters
filtered_df = df[
    (df["edge"] >= edge_filter) & 
    (df["count"] >= matches_filter)
].sort_values("edge", ascending=False)

# Main data display
st.subheader("Recommended Bets")
st.dataframe(
    filtered_df.style
    .bar(subset=["edge"], color="#5fba7d")
    .highlight_max(subset=["edge"], color="lightgreen")
    .format({"line": "{:.1f}", "mean": "{:.1f}", "edge": "{:.1f}"}),
    height=600,
    use_container_width=True,
    column_config={
        "name": "Player",
        "line": "Bet Line",
        "mean": "Avg Kills",
        "count": "Matches",
        "edge": "Edge"
    }
)

# Refresh and footer
st.button("🔄 Refresh Data", type="primary", help="Get the latest stats")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("---")
st.info("ℹ️ Data updates hourly. Edge = (Avg Kills - Bet Line)")

# ======================
# 3. DEPLOYMENT NOTES
# ======================
"""
For Streamlit Cloud deployment:
1. Create requirements.txt with:
streamlit==1.35.0
pandas==2.2.2
requests==2.32.3
beautifulsoup4==4.13.4
lxml==5.2.2

2. Remove any Selenium-related code
3. This version uses pure requests+BS4 scraping
"""
