import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ========== [1. Enhanced Scraping with Selenium] ==========
def setup_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    return webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

def scrape_underdog_with_selenium():
    driver = setup_selenium()
    try:
        driver.get("https://underdogfantasy.com/pick-em/higher-lower/all/val")
        time.sleep(5)  # Wait for JS rendering
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        players = []
        for card in soup.select('div.player-line'):
            try:
                players.append({
                    'name': card.select_one('div.player-name').text.strip(),
                    'line': float(card.select_one('div.line-value').text.strip()),
                    'team': card.select_one('div.player-team').text.strip(),
                    'scraped_at': datetime.now(pytz.UTC)
                })
            except:
                continue
        return pd.DataFrame(players)
    finally:
        driver.quit()

# ========== [2. VLR.gg Match Scraper] ==========
def scrape_vlr_matches():
    try:
        url = "https://www.vlr.gg/matches"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        matches = []
        for match in soup.select('a.match-item'):
            try:
                matches.append({
                    'team1': match.select_one('div.mod-1').text.strip(),
                    'team2': match.select_one('div.mod-2').text.strip(),
                    'event': match.select_one('div.match-item-event').text.strip(),
                    'time': match.select_one('div.match-item-time').text.strip(),
                    'link': f"https://www.vlr.gg{match['href']}"
                })
            except:
                continue
        return pd.DataFrame(matches)
    except Exception as e:
        st.error(f"VLR scrape failed: {str(e)}")
        return pd.DataFrame()

# ========== [3. Prediction Engine] ==========
def calculate_predictions(lines_df, matches_df):
    predictions = []
    for _, row in lines_df.iterrows():
        try:
            # Get matchup data
            match = matches_df[
                (matches_df['team1'].str.contains(row['team'])) | 
                (matches_df['team2'].str.contains(row['team']))
            ].iloc[0]
            
            opponent = match['team2'] if match['team1'] == row['team'] else match['team1']
            
            # Advanced prediction model (simplified example)
            mu = row['line'] * 1.1  # Expected mean
            sigma = 2.5  # Standard deviation
            prob_over = 1 - stats.norm.cdf(row['line'], mu, sigma)
            
            predictions.append({
                'Player': row['name'],
                'Line': row['line'],
                'Team': row['team'],
                'Opponent': opponent,
                'Event': match['event'],
                'Time': match['time'],
                'P(OVER)': f"{prob_over:.0%}",
                'Verdict': "OVER" if prob_over > 0.6 else "UNDER",
                'Confidence': "High" if abs(prob_over - 0.5) > 0.3 else "Medium"
            })
        except:
            continue
    return pd.DataFrame(predictions)

# ========== [4. Chatbot System] ==========
class EsportsAnalyst:
    def generate_response(self, query, predictions):
        if "over" in query.lower() or "under" in query.lower():
            filtered = predictions[predictions['Verdict'] == query.upper().split()[-1]]
            return filtered.to_markdown()
        elif "player" in query.lower():
            player = query.split()[-1]
            return predictions[predictions['Player'] == player].to_markdown()
        else:
            return "Ask about: 'OVER predictions', 'UNDER predictions', or 'Player [name]'"

# ========== [5. Streamlit UI] ==========
def main():
    st.set_page_config(layout="wide", page_title="VALORANT Line Predictor Pro")
    
    # Data Loading
    with st.spinner("Loading live data..."):
        lines = scrape_underdog_with_selenium()
        matches = scrape_vlr_matches()
        predictions = calculate_predictions(lines, matches)
        analyst = EsportsAnalyst()
    
    # Main Display
    st.title("🔫 VALORANT Line Predictor Pro")
    st.dataframe(
        predictions.style.applymap(
            lambda x: "background-color: #4CAF50" if x == "OVER" else "background-color: #F44336",
            subset=['Verdict']
        ),
        use_container_width=True
    )
    
    # Chatbot
    st.sidebar.header("🤖 Esports Analyst")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    
    for msg in st.session_state.chat:
        st.sidebar.write(msg)
    
    if prompt := st.sidebar.text_input("Ask about predictions"):
        response = analyst.generate_response(prompt, predictions)
        st.session_state.chat.append(f"You: {prompt}")
        st.session_state.chat.append(f"Bot: {response}")
        st.sidebar.rerun()

if __name__ == "__main__":
    main()
