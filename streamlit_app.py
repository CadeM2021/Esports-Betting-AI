import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import time
# Add at the top:
from utils.browser import init_driver

# Usage example:
def scrape_underdog():
    driver = init_driver()
    try:
        driver.get("https://underdogfantasy.com")
        # ... scraping logic ...
    finally:
        driver.quit()
# ======================
# 1. CORE SCRAPING FUNCTIONS
# ======================
def scrape_underdog_lines():
    """Scrape ALL player kill lines from Underdog"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    def scrape_underdog_lines():
    driver = init_driver()
    try:
        driver.get("https://underdogfantasy.com")
        # Add your scraping logic here
        return pd.DataFrame()  # Return your scraped data
    finally:
        driver.quit()
    try:
        driver.get("https://underdogfantasy.com/pick-em/higher-lower")
        time.sleep(5)  # Wait for JS loading
        
        players = []
        for elem in driver.find_elements("css selector", "div.player-line"):
            name = elem.find_element("css selector", "div.player-name").text
            line = float(elem.find_element("css selector", "div.line-value").text)
            players.append({"name": name, "line": line})
            
        return pd.DataFrame(players)
    finally:
        driver.quit()

def scrape_vlr_stats():
    """Scrape recent match stats from VLR.gg"""
    url = "https://www.vlr.gg/matches"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    stats = []
    for match in soup.select("div.wf-card.mod-match"):
        for player in match.select("div.player"):
            name = player.select_one("div.player-name").text.strip()
            kills = int(player.select_one("span.mod-kills").text)
            stats.append({"name": name, "kills": kills})
    
    return pd.DataFrame(stats)

# ======================
# 2. STREAMLIT UI
# ======================
st.title("🔫 Valorant Player Kill Dashboard")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data():
    with st.spinner("📡 Loading live data..."):
        lines_df = scrape_underdog_lines()
        stats_df = scrape_vlr_stats()
        
        # Merge datasets
        merged = pd.merge(
            lines_df, 
            stats_df.groupby("name")["kills"].agg(["mean", "count"]).reset_index(),
            on="name"
        )
        merged["edge"] = merged["mean"] - merged["line"]
        return merged.sort_values("edge", ascending=False)

df = load_data()

# Display interactive table
st.dataframe(
    df.style
    .bar(subset=["edge"], align="mid", color=["#FF6B6B", "#4ECDC4"])
    .highlight_max(subset=["edge"], color="lightgreen")
    .format({"mean": "{:.1f}", "edge": "{:.1f}"}),
    height=800,
    use_container_width=True
)

# Add filters
col1, col2 = st.columns(2)
with col1:
    min_edge = st.slider("Minimum Edge", -5.0, 10.0, 1.0)
with col2:
    min_matches = st.slider("Minimum Matches", 1, 20, 5)

filtered = df[(df["edge"] >= min_edge) & (df["count"] >= min_matches)]
st.metric("Value Bets Found", len(filtered))

# ======================
# 3. AUTO-REFRESH LOGIC
# ======================
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.caption("Data updates hourly | Last refresh: " + pd.Timestamp.now().strftime("%H:%M"))
