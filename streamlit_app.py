import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ======================
# 1. CORE FUNCTIONS
# ======================

# Sample data fallback
SAMPLE_PLAYERS = pd.DataFrame({
    "name": ["PlayerA", "PlayerB", "PlayerC"],
    "line": [18.5, 22.5, 20.0],
    "mean": [19.2, 23.1, 21.5],
    "count": [5, 5, 5],
    "edge": [0.7, 0.6, 1.5]
})

SAMPLE_MATCHES = pd.DataFrame({
    "team1": ["Team Liquid", "Fnatic"],
    "team2": ["Sentinels", "NRG"],
    "time": ["10:00 PM", "11:30 PM"],
    "event": ["Champions Tour", "Masters"],
    "link": ["https://www.vlr.gg/123", "https://www.vlr.gg/456"]
})

def safe_scrape(url, css_selector):
    """Universal scraping function with error handling"""
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
        st.warning(f"⚠️ Couldn't scrape {url.split('//')[1].split('/')[0]}")
        return []

def get_player_stats():
    """Get player stats from multiple sources"""
    try:
        # Scrape betting lines
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

        # Scrape performance stats
        stats = []
        matches = safe_scrape("https://www.vlr.gg/matches", "div.wf-card.mod-match")
        
        for match in matches[:10]:
            try:
                stats.append({
                    "name": match.select_one("div.player-name").text.strip(),
                    "kills": int(match.select_one("span.mod-kills").text)
                })
            except:
                continue

        # Process and merge data
        if lines and stats:
            lines_df = pd.DataFrame(lines)
            stats_df = pd.DataFrame(stats)
            stats_agg = stats_df.groupby("name")["kills"].agg(["mean", "count"]).reset_index()
            
            merged = pd.merge(lines_df, stats_agg, on="name", how="left").dropna()
            merged["edge"] = merged["mean"] - merged["line"]
            return merged.sort_values("edge", ascending=False)
            
    except Exception as e:
        st.error(f"🚨 Data processing error: {str(e)}")
        return SAMPLE_PLAYERS

def get_upcoming_matches():
    """Get scheduled matches from VLR.gg"""
    try:
        matches = []
        elements = safe_scrape("https://www.vlr.gg/matches", "a.match-item")
        
        for elem in elements[:12]:
            try:
                matches.append({
                    "team1": elem.select_one(".match-item-vs-team-name.mod-1").text.strip(),
                    "team2": elem.select_one(".match-item-vs-team-name.mod-2").text.strip(),
                    "time": elem.select_one(".match-item-time").text.strip(),
                    "event": elem.select_one(".match-item-event").text.strip(),
                    "link": f"https://www.vlr.gg{elem['href']}"
                })
            except:
                continue
                
        return pd.DataFrame(matches)
    except Exception as e:
        st.error(f"Match schedule error: {str(e)}")
        return SAMPLE_MATCHES

def calculate_value_bets(players_df, matches_df):
    """Identify best bets for upcoming matches"""
    try:
        # Find players in upcoming matches
        merged = pd.merge(
            players_df,
            matches_df,
            how="cross"
        )
        
        # Create filter mask first for clarity
        mask = merged.apply(
            lambda x: (
                str(x['name']) in str(x['team1']) or 
                str(x['name']) in str(x['team2'])
            ),
            axis=1
        )
        
        merged = merged[mask]  # Apply the filter
        
        # Calculate value metrics
        merged["value_score"] = merged["edge"] * merged["count"]
        merged["bet_confidence"] = pd.cut(
            merged["count"],
            bins=[0, 3, 7, 20],
            labels=["Low", "Medium", "High"]
        )
        
        return merged.sort_values(["value_score", "edge"], ascending=False)
    except Exception as e:
        st.error(f"Value bet analysis error: {str(e)}")
        return pd.DataFrame()

# ======================
# 2. STREAMLIT UI
# ======================

st.set_page_config(
    page_title="Valorant Predictor Pro",
    page_icon="🔫",
    layout="wide"
)

# Title and description
st.title("🎯 Valorant Predictive Dashboard")
st.caption("Compare betting lines to player performance to find value bets")

# Data loading with caching
@st.cache_data(ttl=3600)
def load_all_data():
    with st.spinner("🔄 Loading latest data..."):
        return {
            "players": get_player_stats(),
            "matches": get_upcoming_matches()
        }

data = load_all_data()
players_df = data["players"]
matches_df = data["matches"]

# Dashboard Metrics
st.subheader("Live Insights")
metric_cols = st.columns(4)
metric_cols[0].metric("Active Players", len(players_df))
metric_cols[1].metric("Upcoming Matches", len(matches_df))
metric_cols[2].metric("Avg Edge", f"{players_df['edge'].mean():.1f}")
metric_cols[3].metric("Top Value", f"{players_df['edge'].max():.1f}")

# Main filters
with st.expander("🔍 Filter Options", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        edge_filter = st.slider("Minimum Edge", -2.0, 5.0, 0.5, 0.1)
    with col2:
        matches_filter = st.slider("Minimum Matches", 1, 20, 3)

# Filter players
filtered_players = players_df[
    (players_df["edge"] >= edge_filter) & 
    (players_df["count"] >= matches_filter)
]

# Player stats display
st.subheader("📊 Player Statistics")
st.dataframe(
    filtered_players.style
    .bar(subset=["edge"], color="#5fba7d")
    .highlight_max(subset=["edge"], color="lightgreen")
    .format({"line": "{:.1f}", "mean": "{:.1f}", "edge": "{:.1f}"}),
    height=400,
    use_container_width=True,
    column_config={
        "name": "Player",
        "line": "Bet Line",
        "mean": "Avg Kills",
        "count": "Matches",
        "edge": "Edge"
    }
)

# Upcoming matches display
st.subheader("📅 Upcoming Matches")
st.dataframe(
    matches_df,
    height=250,
    use_container_width=True,
    hide_index=True,
    column_config={
        "team1": "Team 1",
        "team2": "Team 2",
        "time": "Start Time",
        "event": "Event",
        "link": st.column_config.LinkColumn("Details")
    }
)

# Value bets analysis
st.subheader("💎 Top Value Bets")
value_bets = calculate_value_bets(filtered_players, matches_df)

if not value_bets.empty:
    st.dataframe(
        value_bets.head(15),
        height=500,
        use_container_width=True,
        column_config={
            "name": "Player",
            "team1": "Team 1",
            "team2": "Team 2",
            "line": "Line",
            "mean": "Avg Kills",
            "edge": "Edge",
            "value_score": "Value Score",
            "bet_confidence": "Confidence"
        }
    )
else:
    st.warning("No strong value bets found in upcoming matches")

# Refresh button
if st.button("🔄 Refresh All Data", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Footer
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.markdown("---")
st.info("ℹ️ Edge = (Avg Kills - Bet Line). Higher values indicate better bets.")
