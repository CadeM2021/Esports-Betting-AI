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
    """Scrape real player lines from Underdog's Valorant tabs"""
    valorant_urls = [
        "https://underdogfantasy.com/pick-em/higher-lower/all/val",
        "https://underdogfantasy.com/pick-em/higher-lower/all/esports"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_players = []
    
    for url in valorant_urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for player in soup.select("div.player-line"):
                try:
                    name = player.select_one("div.player-name").get_text(strip=True)
                    line = float(player.select_one("div.line-value").get_text(strip=True))
                    team = player.select_one("div.player-team").get_text(strip=True) if player.select_one("div.player-team") else "Unknown"
                    
                    # Only include clear Valorant players
                    if any(x in name.lower() for x in ['vct', 'valorant']):
                        all_players.append({
                            'player': name,
                            'line': line,
                            'team': team,
                            'source': url.split('/')[-1]
                        })
                except Exception as e:
                    continue
                    
        except Exception as e:
            st.warning(f"Underdog scrape failed for {url}: {str(e)}")
            continue
    
    return pd.DataFrame(all_players) if all_players else None

def scrape_vlr_match_details():
    """Get detailed match results from VLR.gg"""
    try:
        url = "https://www.vlr.gg/matches"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        matches = []
        
        # Process completed matches from last 7 days
        for match in soup.select("a.match-item"):
            try:
                date_str = match.select_one("div.match-item-date").get_text(strip=True)
                match_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                if match_date > datetime.now() - timedelta(days=7):
                    team1 = match.select_one("div.match-item-vs-team-name.mod-1").get_text(strip=True)
                    team2 = match.select_one("div.match-item-vs-team-name.mod-2").get_text(strip=True)
                    event = match.select_one("div.match-item-event").get_text(strip=True)
                    match_url = f"https://www.vlr.gg{match['href']}"
                    
                    # Get detailed match data
                    match_response = requests.get(match_url, headers=headers, timeout=15)
                    match_soup = BeautifulSoup(match_response.text, 'html.parser')
                    
                    # Extract player stats
                    for player_row in match_soup.select("table.wf-table-inset.mod-overview tbody tr"):
                        player_name = player_row.select_one("td.mod-player").get_text(strip=True)
                        kills = int(player_row.select_one("td.mod-kills").get_text(strip=True))
                        deaths = int(player_row.select_one("td.mod-deaths").get_text(strip=True))
                        agent = player_row.select_one("td.mod-agents").get_text(strip=True)
                        
                        matches.append({
                            'player': player_name,
                            'team': team1 if player_name in team1 else team2,
                            'kills': kills,
                            'deaths': deaths,
                            'agent': agent,
                            'vs_team': team2 if player_name in team1 else team1,
                            'date': match_date,
                            'event': event
                        })
            except Exception as e:
                continue
                
        return pd.DataFrame(matches) if matches else None
        
    except Exception as e:
        st.error(f"VLR.gg detailed scrape failed: {str(e)}")
        return None

# ======================
# 2. PLAYER ANALYSIS ENGINE
# ======================

def generate_player_reports(underdog_df, vlr_df):
    """Create detailed analysis for each player"""
    try:
        if underdog_df is None or vlr_df is None:
            raise ValueError("Missing source data")
            
        # Calculate player stats
        player_stats = vlr_df.groupby(['player', 'team']).agg({
            'kills': ['mean', 'max', 'min', 'count'],
            'deaths': 'mean',
            'agent': lambda x: x.mode()[0]
        }).reset_index()
        
        player_stats.columns = ['player', 'team', 'avg_kills', 'max_kills', 'min_kills', 
                              'matches_played', 'avg_deaths', 'main_agent']
        
        # Merge with betting lines
        merged = pd.merge(
            underdog_df,
            player_stats,
            left_on=['player', 'team'],
            right_on=['player', 'team'],
            how='inner'
        )
        
        # Calculate predictions
        merged['edge'] = merged['avg_kills'] - merged['line']
        merged['hit_prob'] = np.clip(0.5 + (merged['edge']/5), 0.3, 0.9)
        
        # Add matchup analysis
        merged['recent_opponents'] = merged['player'].apply(
            lambda x: vlr_df[vlr_df['player'] == x]['vs_team'].unique()[:3].tolist()
        )
        
        # Categorize predictions
        conditions = [
            (merged['hit_prob'] > 0.7),
            (merged['hit_prob'] > 0.6),
            (merged['hit_prob'] > 0.5)
        ]
        choices = ['STRONG OVER', 'MODERATE OVER', 'SLIGHT OVER']
        merged['prediction'] = np.select(conditions, choices, default='UNDER')
        
        return merged.sort_values('hit_prob', ascending=False)
        
    except Exception as e:
        st.warning(f"Analysis error: {str(e)}")
        return None

# ======================
# 3. STREAMLIT UI WITH DETAILED REPORTS
# ======================

def display_player_report(player_data):
    """Show detailed analysis for a single player"""
    with st.expander(f"🔍 Detailed Analysis: {player_data['player']}", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Bet Line", f"{player_data['line']:.1f}")
        col2.metric("7-Day Avg", f"{player_data['avg_kills']:.1f}")
        col3.metric("Hit Probability", f"{player_data['hit_prob']:.0%}")
        
        st.write(f"**Team:** {player_data['team']}")
        st.write(f"**Main Agent:** {player_data['main_agent']}")
        st.write(f"**Recent Form:** {player_data['matches_played']} matches ({player_data['min_kills']}-{player_data['max_kills']} kills range)")
        
        st.write("**Recent Opponents:**")
        for opponent in player_data['recent_opponents']:
            st.write(f"- {opponent}")
        
        st.write(f"**Prediction Rationale:**")
        if player_data['prediction'] in ['STRONG OVER', 'MODERATE OVER']:
            st.success(f"{player_data['player']} has consistently outperformed this line, averaging {player_data['avg_kills']:.1f} kills over their last {player_data['matches_played']} matches against quality opponents.")
        else:
            st.warning(f"Caution advised - {player_data['player']}'s recent average of {player_data['avg_kills']:.1f} kills is below their current line.")

def main():
    st.set_page_config(
        page_title="Valorant Predictive Analytics",
        layout="wide"
    )
    st.title("🎯 Valorant Player Line Predictions")
    
    # Data loading
    with st.spinner("Loading live player data and match histories..."):
        underdog_data = scrape_underdog_lines()
        vlr_data = scrape_vlr_match_details()
        
        predictions = generate_player_reports(underdog_data, vlr_data)
        
        if predictions is None or predictions.empty:
            st.error("⚠️ Couldn't load live data - showing sample analysis")
            predictions = pd.DataFrame({
                'player': ['aspas', 'Derke', 'cNed'],
                'team': ['LOUD', 'Fnatic', 'NAVI'],
                'line': [18.5, 22.5, 20.0],
                'avg_kills': [19.2, 23.1, 21.5],
                'matches_played': [5, 5, 5],
                'main_agent': ['Jett', 'Raze', 'Jett'],
                'hit_prob': [0.72, 0.65, 0.58],
                'prediction': ['STRONG OVER', 'MODERATE OVER', 'SLIGHT OVER'],
                'recent_opponents': [['NRG', 'Sentinels', '100T'], ['Team Liquid', 'DRX', 'LOUD'], ['Fnatic', 'G2', 'KOI']]
            })
    
    # Main display
    st.subheader("🔥 Top Value Plays Today")
    
    # Show top 5 predictions
    top_plays = predictions.head(5)
    
    for _, play in top_plays.iterrows():
        display_player_report(play)
    
    # Full predictions table
    st.subheader("📊 All Player Predictions")
    st.dataframe(
        predictions[['player', 'team', 'line', 'avg_kills', 'matches_played', 'prediction']],
        column_config={
            'player': 'Player',
            'team': 'Team',
            'line': 'Bet Line',
            'avg_kills': 'Avg Kills',
            'matches_played': 'Matches',
            'prediction': 'Verdict'
        },
        height=600,
        use_container_width=True
    )
    
    if st.button("🔄 Refresh All Data", type="primary"):
        st.rerun()
    
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    main()
