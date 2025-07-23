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
    """Robust Underdog Fantasy API scraper with multiple fallbacks"""
    try:
        # Try direct API first
        api_url = "https://api.underdogfantasy.com/beta/v3/over_under_lines"
        params = {'game': 'valorant', 'stat': 'kills'}
        
        response = requests.get(
            api_url,
            headers={'User-Agent': 'Mozilla/5.0'},
            params=params,
            timeout=10
        )
        data = response.json()
        
        if 'lines' not in data:
            raise ValueError("Unexpected API response format")
            
        return pd.DataFrame([{
            'name': line['player_name'],
            'line': float(line['stat_value']),
            'match_id': line.get('match_id', ''),
            'start_time': line.get('match_start_time', '')
        } for line in data['lines'] if 'player_name' in line])
        
    except Exception as api_error:
        st.warning(f"Underdog API failed, trying HTML scrape... Error: {str(api_error)}")
        try:
            # Fallback to HTML scraping
            response = requests.get(
                "https://underdogfantasy.com/pick-em/higher-lower",
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
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
            
        except Exception as html_error:
            st.error(f"Underdog scraping failed: {str(html_error)}")
            return None

def scrape_vlr_stats(days_back=7):
    """Robust VLR.gg scraper with error handling"""
    try:
        stats = []
        for page in range(1, 4):  # Only first 3 pages for reliability
            url = f"https://www.vlr.gg/stats/?page={page}"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
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
            ['mean', 'count', 'std']
        ).reset_index()
        player_stats = player_stats[player_stats['count'] >= 3]  # Min 3 matches
        
        # Merge with betting lines
        merged = pd.merge(
            underdog_df,
            player_stats,
            on='name',
            how='left'
        ).dropna()
        
        # Calculate predictions
        merged['hit_prob'] = 1 - merged.apply(
            lambda x: norm.cdf(x['line'], x['mean'], x['std']),
            axis=1
        )
        merged['prediction'] = np.where(
            merged['hit_prob'] > 0.6, 
            'STRONG HIT',
            np.where(merged['hit_prob'] > 0.5, 'WEAK HIT', 'UNDER')
        )
        
        return merged.sort_values('hit_prob', ascending=False)
        
    except Exception as e:
        st.warning(f"Analysis error: {str(e)}")
        return None

# ======================
# 3. STREAMLIT UI
# ======================

def main():
    st.set_page_config(
        page_title="Valorant Predictor Pro",
        layout="wide"
    )
    st.title("🎯 Valorant Line Prediction Engine")
    
    # Data loading section
    with st.spinner("🔄 Loading live data from Underdog Fantasy and VLR.gg..."):
        underdog_data = scrape_underdog_lines()
        vlr_data = scrape_vlr_stats()
        
        if underdog_data is not None and vlr_data is not None:
            predictions = analyze_data(underdog_data, vlr_data)
        else:
            st.warning("Using sample data due to scraping issues")
            predictions = pd.DataFrame({
                'name': ['PlayerA', 'PlayerB', 'PlayerC'],
                'line': [18.5, 22.5, 20.0],
                'mean': [19.2, 23.1, 21.5],
                'count': [5, 5, 5],
                'std': [1.2, 1.5, 1.3],
                'hit_prob': [0.72, 0.65, 0.58],
                'prediction': ['STRONG HIT', 'STRONG HIT', 'WEAK HIT']
            })
    
    # Main display
    st.subheader("🔥 Today's Best Bets")
    
    if predictions is not None:
        # Prediction tiers
        strong_hits = predictions[predictions['prediction'] == 'STRONG HIT']
        weak_hits = predictions[predictions['prediction'] == 'WEAK HIT']
        
        # Display strong hits
        st.markdown("### 💎 Strong Plays (60%+ Hit Probability)")
        st.dataframe(
            strong_hits.style
            .background_gradient(subset=['hit_prob'], cmap='Greens')
            .format({'line': '{:.1f}', 'mean': '{:.1f}', 'hit_prob': '{:.0%}'}),
            column_config={
                'name': 'Player',
                'line': 'Bet Line',
                'mean': 'Avg Kills',
                'count': 'Matches',
                'hit_prob': 'Hit %',
                'prediction': 'Verdict'
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Display weak hits
        st.markdown("### ⚠️ Marginal Plays (50-60% Hit Probability)")
        st.dataframe(
            weak_hits.style
            .background_gradient(subset=['hit_prob'], cmap='YlOrBr')
            .format({'line': '{:.1f}', 'mean': '{:.1f}', 'hit_prob': '{:.0%}'}),
            hide_index=True,
            use_container_width=True
        )
    
    # Refresh controls
    st.button("🔄 Refresh All Data", type="primary")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    main()
