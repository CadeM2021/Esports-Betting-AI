import streamlit as st
import pandas as pd
import requests
import os
import sys
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ======================
# 1. BROWSER INITIALIZATION
# ======================
def init_driver():
    """Robust ChromeDriver initialization with multiple fallbacks"""
    options = Options()
    
    # Essential configuration
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # Anti-bot measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        # Attempt to use system Chrome in Docker environment
        if os.path.exists("/usr/bin/google-chrome"):
            options.binary_location = "/usr/bin/google-chrome"
            service = Service("/usr/bin/chromedriver")
            return webdriver.Chrome(service=service, options=options)
        
        # Fallback to webdriver-manager
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
    except Exception as e:
        st.error(f"Browser initialization failed: {str(e)}")
        return None

# ======================
# 2. SCRAPING FUNCTIONS
# ======================
def scrape_underdog_lines():
    """Scrape player kill lines from Underdog Fantasy"""
    driver = None
    try:
        driver = init_driver()
        if not driver:
            st.warning("Using sample data due to browser initialization failure")
            return pd.DataFrame({
                "name": ["Player1", "Player2", "Player3"],
                "line": [22.5, 18.5, 20.0]
            })
            
        driver.get("https://underdogfantasy.com/pick-em/higher-lower")
        time.sleep(5)  # Wait for page to load
        
        players = []
        player_elements = driver.find_elements("css selector", "div.player-line")
        
        for elem in player_elements[:15]:  # Limit to 15 players
            try:
                name = elem.find_element("css selector", "div.player-name").text
                line = float(elem.find_element("css selector", "div.line-value").text)
                players.append({"name": name, "line": line})
            except Exception as e:
                st.warning(f"Failed to parse player: {str(e)}")
                continue
                
        return pd.DataFrame(players) if players else pd.DataFrame({"name": [], "line": []})
        
    except Exception as e:
        st.error(f"Scraping failed: {str(e)}")
        return pd.DataFrame({"name": [], "line": []})
    finally:
        if driver:
            driver.quit()

def scrape_vlr_stats():
    """Scrape recent match stats from VLR.gg"""
    try:
        url = "https://www.vlr.gg/matches"
        response = requests.get(url, timeout=10)
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
# 3. STREAMLIT APP
# ======================
st.title("🔫 Valorant Player Kill Dashboard")

@st.cache_data(ttl=3600)
def load_data():
    with st.spinner("📡 Loading live data..."):
        lines_df = scrape_underdog_lines()
        stats_df = scrape_vlr_stats()
        
        if lines_df.empty or stats_df.empty:
            st.warning("Some data sources failed - using partial data")
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
        )
        merged["edge"] = merged["mean"] - merged["line"]
        return merged.sort_values("edge", ascending=False)

df = load_data()

# Display data
if not df.empty:
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
