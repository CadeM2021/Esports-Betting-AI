import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import numpy as np

# ======================
# 1. UNDERDOG FANTASY SCRAPER
# ======================

def scrape_underdog_lines():
    """Scrape from Underdog's Valorant-specific tabs"""
    valorant_urls = [
        "https://underdogfantasy.com/pick-em/higher-lower/all/val",
        "https://underdogfantasy.com/pick-em/higher-lower/all/esports"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    all_players = []
    
    for url in valorant_urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract player lines
            for player in soup.select("div.player-line"):
                try:
                    name = player.select_one("div.player-name").get_text(strip=True)
                    line = float(player.select_one("div.line-value").get_text(strip=True))
                    
                    # Simple Valorant player validation
                    if any(x in name.lower() for x in ['vct', 'valorant', 'champions']):
                        all_players.append({
                            'name': name,
                            'line': line,
                            'source': 'Underdog'
                        })
                except:
                    continue
                    
        except Exception as e:
            st.warning(f"Underdog scrape failed for {url}: {str(e)}")
            continue
    
    return pd.DataFrame(all_players) if all_players else None

# ======================
# 2. VLR.GG MATCHES SCRAPER
# ======================

def scrape_vlr_matches(days_back=3):
    """Scrape player stats from recent matches on VLR.gg"""
    try:
        url = "https://www.vlr.gg/matches"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        stats = []
        
        # Process completed matches first
        for match in soup.select("div.wf-card.mod-match.mod-completed"):
            try:
                match_date_str = match.select_one("div.match-item-eta").get_text(strip=True)
                match_date = datetime.strptime(match_date_str, '%Y-%m-%d')
                
                if match_date > datetime.now() - timedelta(days=days_back):
                    for player in match.select("div.player"):
                        try:
                            stats.append({
                                'name': player.select_one("div.player-name").get_text(strip=True),
                                'kills': int(player.select_one("span.mod-kills").text),
                                'date': match_date
                            })
                        except:
                            continue
            except:
                continue
        
        return pd.DataFrame(stats) if stats else None
        
    except Exception as e:
        st.error(f"VLR.gg matches scrape failed: {str(e)}")
        return None

# ======================
# 3. DATA ANALYSIS & UI
# ======================

def analyze_performance(underdog_df, vlr_df):
    """Generate predictions from scraped data"""
    try:
        if underdog_df is None or vlr_df is None:
            raise ValueError("Missing source data")
            
        # Calculate player stats (min 2 matches)
        player_stats = vlr_df.groupby('name')['kills'].agg(
            ['mean', 'count', 'std']
        ).reset_index()
        player_stats = player_stats[player_stats['count'] >= 2]
        
        # Merge with betting lines
        merged = pd.merge(
            underdog_df,
            player_stats,
            on='name',
            how='inner'
        )
        
        # Calculate predictions
        merged['edge'] = merged['mean'] - merged['line']
        merged['hit_prob'] = np.clip(0.5 + (merged['edge']/10), 0.2, 0.8)  # Normalized probability
        
        # Categorize predictions
        conditions = [
            (merged['hit_prob'] > 0.65),
            (merged['hit_prob'] > 0.55)
        ]
        choices = ['STRONG HIT', 'WEAK HIT']
        merged['prediction'] = np.select(conditions, choices, default='UNDER')
        
        return merged.sort_values('hit_prob', ascending=False)
        
    except Exception as e:
        st.warning(f"Analysis error: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="Valorant Predictor Pro",
        layout="wide"
    )
    st.title("🎯 Valorant Line Prediction Engine")
    
    # Data loading
    with st.spinner("Loading live data from Underdog & VLR.gg..."):
        underdog_data = scrape_underdog_lines()
        vlr_data = scrape_vlr_matches()
        
        predictions = analyze_performance(underdog_data, vlr_data)
        
        if predictions is None or predictions.empty:
            st.warning("Using sample data due to scraping issues")
            predictions = pd.DataFrame({
                'name': ['PlayerA', 'PlayerB', 'PlayerC'],
                'line': [18.5, 22.5, 20.0],
                'mean': [19.2, 23.1, 21.5],
                'count': [5, 5, 5],
                'edge': [0.7, 0.6, 1.5],
                'hit_prob': [0.72, 0.65, 0.58],
                'prediction': ['STRONG HIT', 'STRONG HIT', 'WEAK HIT']
            })
    
    # Display predictions
    st.subheader("🔥 Today's Best Value Bets")
    
    # Format display
    display_cols = ['name', 'line', 'mean', 'count', 'edge', 'hit_prob', 'prediction']
    display_df = predictions[display_cols].copy()
    display_df['hit_prob'] = display_df['hit_prob'].apply(lambda x: f"{x:.0%}")
    
    # Color coding
    def color_prediction(val):
        if val == 'STRONG HIT':
            return 'background-color: #4CAF50; color: white'
        elif val == 'WEAK HIT':
            return 'background-color: #FFC107; color: black'
        else:
            return 'background-color: #F44336; color: white'
    
    st.dataframe(
        display_df.style.applymap(color_prediction, subset=['prediction']),
        column_config={
            'name': 'Player',
            'line': 'Bet Line',
            'mean': 'Avg Kills',
            'count': 'Matches',
            'edge': 'Edge',
            'hit_prob': 'Hit %',
            'prediction': 'Verdict'
        },
        height=600,
        use_container_width=True
    )
    
    # Refresh button
    if st.button("🔄 Refresh Data", type="primary"):
        st.rerun()
    
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    main()
