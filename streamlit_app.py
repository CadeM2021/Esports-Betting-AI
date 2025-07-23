import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import json

# ======================
# 1. CORE SCRAPING FUNCTIONS
# ======================

def scrape_underdog_lines():
    """Scrape real betting lines from Underdog Fantasy"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        # Underdog's API endpoint (found through browser inspection)
        url = "https://api.underdogfantasy.com/beta/v3/over_under_lines"
        params = {
            'game': 'valorant',
            'stat': 'kills',
            'period': 'match'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        players = []
        
        for line in data['lines']:
            players.append({
                'name': line['player_name'],
                'line': float(line['stat_value']),
                'match_id': line['match_id'],
                'start_time': line['match_start_time']
            })
            
        return pd.DataFrame(players)
        
    except Exception as e:
        st.error(f"Underdog API error: {str(e)}")
        return None

def scrape_vlr_stats(days_back=7):
    """Scrape player stats from VLR.gg with date filtering"""
    try:
        base_url = "https://www.vlr.gg/stats"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # Get last 5 pages of stats (recent matches)
        all_stats = []
        for page in range(1, 6):
            url = f"{base_url}?page={page}"
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse date for each match row
            for row in soup.select("table.wf-table.mod-stats tbody tr"):
                date_str = row.select_one("td.mod-date").text.strip()
                match_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Only include recent matches
                if match_date > datetime.now() - timedelta(days=days_back):
                    all_stats.append({
                        'name': row.select_one("td.mod-player").text.strip(),
                        'kills': int(row.select_one("td.mod-kills").text),
                        'date': match_date
                    })
                    
        return pd.DataFrame(all_stats)
        
    except Exception as e:
        st.error(f"VLR.gg scraping error: {str(e)}")
        return None

# ======================
# 2. DATA ANALYSIS
# ======================

def analyze_performance(player_name, days_back=7):
    """Calculate recent performance metrics for a player"""
    try:
        stats = scrape_vlr_stats(days_back)
        if stats is None or stats.empty:
            return None
            
        player_stats = stats[stats['name'] == player_name]
        if player_stats.empty:
            return None
            
        return {
            'avg_kills': player_stats['kills'].mean(),
            'matches_played': len(player_stats),
            'hit_rate': (player_stats['kills'] > line_value).mean()  # Compared to their line
        }
    except:
        return None

# ======================
# 3. STREAMLIT UI
# ======================

def main():
    st.set_page_config(
        page_title="Valorant Line Predictor",
        layout="wide"
    )
    st.title("🔫 Valorant Line Prediction Dashboard")
    
    # Data loading
    with st.spinner("Loading live data from Underdog Fantasy and VLR.gg..."):
        underdog_df = scrape_underdog_lines()
        vlr_df = scrape_vlr_stats()
        
        # Merge and analyze data
        if underdog_df is not None and vlr_df is not None:
            # Calculate performance stats for each player
            predictions = []
            for _, row in underdog_df.iterrows():
                performance = analyze_performance(row['name'])
                if performance:
                    predictions.append({
                        'Player': row['name'],
                        'Bet Line': row['line'],
                        'Avg Kills (7d)': performance['avg_kills'],
                        'Matches Played': performance['matches_played'],
                        'Hit Rate %': performance['hit_rate'] * 100,
                        'Prediction': 'HIT' if performance['avg_kills'] > row['line'] else 'UNDER'
                    })
            
            predictions_df = pd.DataFrame(predictions)
        else:
            st.warning("Using sample data due to scraping issues")
            predictions_df = pd.DataFrame({
                'Player': ['PlayerA', 'PlayerB', 'PlayerC'],
                'Bet Line': [18.5, 22.5, 20.0],
                'Avg Kills (7d)': [19.2, 23.1, 21.5],
                'Matches Played': [5, 5, 5],
                'Hit Rate %': [80, 75, 85],
                'Prediction': ['HIT', 'HIT', 'HIT']
            })
    
    # Display predictions
    st.subheader("🎯 Today's Predictions")
    st.dataframe(
        predictions_df.style
        .applymap(lambda x: 'background-color: #4CAF50' if x == 'HIT' else 'background-color: #F44336', 
                 subset=['Prediction'])
        .format({'Avg Kills (7d)': '{:.1f}', 'Hit Rate %': '{:.0f}%'}),
        height=600,
        use_container_width=True
    )
    
    # Match schedule
    if underdog_df is not None:
        st.subheader("📅 Upcoming Matches")
        matches = underdog_df[['match_id', 'start_time']].drop_duplicates()
        st.dataframe(matches, height=200)
    
    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.rerun()

if __name__ == "__main__":
    main()
