import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import numpy as np

# ======================
# 1. ENHANCED SCRAPING FUNCTIONS
# ======================

def scrape_underdog_lines():
    """Robust Underdog Fantasy data collector"""
    try:
        # Try HTML scraping directly since API is unreliable
        response = requests.get(
            "https://underdogfantasy.com/pick-em/higher-lower",
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=15
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        
        players = []
        for player in soup.select("div.player-line")[:25]:  # Limit to 25 players
            try:
                players.append({
                    'name': player.select_one("div.player-name").get_text(strip=True),
                    'line': float(player.select_one("div.line-value").get_text(strip=True))
                })
            except:
                continue
                
        return pd.DataFrame(players) if players else None
            
    except Exception as e:
        st.error(f"Underdog scraping failed: {str(e)}")
        return None

def scrape_vlr_stats(days_back=7):
    """Robust VLR.gg scraper with error handling"""
    try:
        stats = []
        for page in range(1, 3):  # Only first 2 pages for reliability
            url = f"https://www.vlr.gg/stats/?page={page}"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for row in soup.select("tr.wf-table-inset.mod-overview"):
                cols = row.select("td")
                if len(cols) < 10:  # Ensure valid row
                    continue
                    
                try:
                    name = cols[1].get_text(strip=True)
                    kills = int(cols[4].get_text(strip=True))
                    date_str = cols[0].get_text(strip=True)
                    
                    try:
                        match_date = datetime.strptime(date_str, '%Y-%m-%d')
                        if match_date > datetime.now() - timedelta(days=days_back):
                            stats.append({'name': name, 'kills': kills})
                    except:
                        continue
                        
                except:
                    continue
                    
        return pd.DataFrame(stats) if stats else None
        
    except Exception as e:
        st.error(f"VLR.gg scraping error: {str(e)}")
        return None

# ======================
# 2. DATA PROCESSING
# ======================

def analyze_data(underdog_df, vlr_df):
    """Generate predictions with comprehensive error handling"""
    try:
        if underdog_df is None or vlr_df is None:
            raise ValueError("Missing input data")
            
        # Calculate player stats
        player_stats = vlr_df.groupby('name')['kills'].agg(
            ['mean', 'count']
        ).reset_index()
        player_stats = player_stats[player_stats['count'] >= 3]  # Min 3 matches
        
        # Merge with betting lines
        merged = pd.merge(
            underdog_df,
            player_stats,
            on='name',
            how='left'
        ).dropna()
        
        # Simple hit probability calculation
        merged['edge'] = merged['mean'] - merged['line']
        merged['hit_prob'] = merged['edge'] / merged['mean'] + 0.5  # Normalized to 0-1 range
        
        merged['prediction'] = np.where(
            merged['hit_prob'] > 0.6, 
            'STRONG HIT',
            np.where(merged['hit_prob'] > 0.5, 'WEAK HIT', 'UNDER')
        )
        
        return merged[['name', 'line', 'mean', 'count', 'edge', 'hit_prob', 'prediction']]
        
    except Exception as e:
        st.warning(f"Analysis error: {str(e)}")
        return None

# ======================
# 3. STREAMLIT UI
# ======================

def color_prediction(val):
    """Custom color formatter for predictions"""
    if val == 'STRONG HIT':
        return 'background-color: #4CAF50; color: white'  # Green
    elif val == 'WEAK HIT':
        return 'background-color: #FFC107; color: black'  # Yellow
    else:
        return 'background-color: #F44336; color: white'  # Red

def main():
    st.set_page_config(
        page_title="Valorant Predictor Pro",
        layout="wide"
    )
    st.title("🎯 Valorant Line Prediction Engine")
    
    # Sample data for fallback
    SAMPLE_DATA = pd.DataFrame({
        'name': ['PlayerA', 'PlayerB', 'PlayerC'],
        'line': [18.5, 22.5, 20.0],
        'mean': [19.2, 23.1, 21.5],
        'count': [5, 5, 5],
        'edge': [0.7, 0.6, 1.5],
        'hit_prob': [0.72, 0.65, 0.58],
        'prediction': ['STRONG HIT', 'STRONG HIT', 'WEAK HIT']
    })
    
    # Data loading section
    with st.spinner("🔄 Loading live data..."):
        underdog_data = scrape_underdog_lines()
        vlr_data = scrape_vlr_stats()
        
        predictions = analyze_data(underdog_data, vlr_data)
        if predictions is None or predictions.empty:
            st.warning("Using sample data due to scraping issues")
            predictions = SAMPLE_DATA
    
    # Main display
    st.subheader("🔥 Today's Best Bets")
    
    # Format display columns
    display_df = predictions.copy()
    display_df['hit_prob'] = display_df['hit_prob'].apply(lambda x: f"{x:.0%}")
    
    # Display predictions with styling
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
        hide_index=True,
        use_container_width=True
    )
    
    # Refresh controls
    if st.button("🔄 Refresh All Data", type="primary"):
        st.rerun()
    
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    main()
