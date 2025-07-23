import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import numpy as np
from pytz import timezone

# ======================
# 1. LIVE DATA SCRAPING
# ======================

def get_current_rosters():
    """Scrape live rosters from VLR.gg"""
    teams = {
        'Sentinels': 'https://www.vlr.gg/team/2/sentinels',
        'LOUD': 'https://www.vlr.gg/team/537/loud',
        'Fnatic': 'https://www.vlr.gg/team/1/fnatic',
        # Add more teams as needed
    }
    
    rosters = {}
    for team, url in teams.items():
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            players = [p.text.strip() for p in soup.select('div.team-roster-item a.team-roster-item-name')]
            rosters[team] = players
        except Exception as e:
            st.warning(f"Couldn't scrape {team} roster: {str(e)}")
            continue
            
    return rosters

def scrape_underdog_lines():
    """Get live player lines from Underdog's VALORANT tabs"""
    urls = [
        "https://underdogfantasy.com/pick-em/higher-lower/all/val",
        "https://underdogfantasy.com/pick-em/higher-lower/all/esports"
    ]
    
    rosters = get_current_rosters()
    lines = []
    
    for url in urls:
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for player in soup.select('div.player-line'):
                try:
                    name = player.select_one('div.player-name').text.strip()
                    line = float(player.select_one('div.line-value').text.strip())
                    team = player.select_one('div.player-team').text.strip() if player.select_one('div.player-team') else None
                    
                    # Validate against current rosters
                    if team and team in rosters and name in rosters[team]:
                        lines.append({
                            'player': name,
                            'line': line,
                            'team': team,
                            'scraped_at': datetime.now(timezone('UTC'))
                        })
                except:
                    continue
        except:
            continue
            
    return pd.DataFrame(lines)

def scrape_upcoming_matches():
    """Get all upcoming matches from VLR.gg (Tier 1 & 2)"""
    try:
        url = "https://www.vlr.gg/matches"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        matches = []
        for match in soup.select('a.match-item'):
            try:
                team1 = match.select_one('div.match-item-vs-team-name.mod-1').text.strip()
                team2 = match.select_one('div.match-item-vs-team-name.mod-2').text.strip()
                event = match.select_one('div.match-item-event').text.strip()
                time = match.select_one('div.match-item-time').text.strip()
                
                matches.append({
                    'team1': team1,
                    'team2': team2,
                    'event': event,
                    'time': time,
                    'match_url': f"https://www.vlr.gg{match['href']}"
                })
            except:
                continue
                
        return pd.DataFrame(matches)
    except Exception as e:
        st.error(f"Match scrape failed: {str(e)}")
        return pd.DataFrame()

# ======================
# 2. PREDICTION ENGINE
# ======================

def analyze_matchup(player_line, opponent_team):
    """Generate prediction based on matchup analysis"""
    # In production, this would use real historical data
    # This is a simplified version for demonstration
    
    # Simulate performance against opponent
    performance_boost = {
        'Weak': 1.2,
        'Average': 1.0,
        'Strong': 0.8
    }
    
    # Get base performance (simulated)
    base_kills = np.random.normal(loc=player_line['line'], scale=2)
    
    # Adjust for opponent strength
    opponent_strength = np.random.choice(['Weak', 'Average', 'Strong'])
    predicted_kills = base_kills * performance_boost[opponent_strength]
    
    return {
        'predicted_kills': round(predicted_kills, 1),
        'over_under': 'OVER' if predicted_kills > player_line['line'] else 'UNDER',
        'confidence': 'High' if abs(predicted_kills - player_line['line']) > 1.5 else 'Medium',
        'matchup_note': f"vs {opponent_team} ({opponent_strength} opponent)"
    }

# ======================
# 3. ESPORTS CHATBOT
# ======================

class EsportsAnalyst:
    def __init__(self):
        self.knowledge_base = {
            'player_stats': {},
            'match_predictions': {}
        }
    
    def analyze_line(self, player_name, line_df, matches_df):
        """Chatbot analysis of a player line"""
        player_data = line_df[line_df['player'] == player_name].iloc[0]
        match = matches_df[
            (matches_df['team1'] == player_data['team']) | 
            (matches_df['team2'] == player_data['team'])
        ].iloc[0]
        
        opponent = match['team2'] if match['team1'] == player_data['team'] else match['team1']
        analysis = analyze_matchup(player_data, opponent)
        
        response = f"""
        **{player_name} Analysis** ({player_data['team']})
        - Current Line: {player_data['line']} kills
        - Predicted: {analysis['predicted_kills']} ({analysis['over_under']})
        - Confidence: {analysis['confidence']}
        - Next Match: vs {opponent} ({match['time']})
        - Note: {analysis['matchup_note']}
        """
        
        return response

# ======================
# 4. STREAMLIT UI
# ======================

def main():
    st.title("🔫 VALORANT Line Predictor Pro")
    st.caption("Live betting line analysis powered by Underdog Fantasy & VLR.gg")
    
    # Load data
    with st.spinner("Loading live data..."):
        lines_df = scrape_underdog_lines()
        matches_df = scrape_upcoming_matches()
        analyst = EsportsAnalyst()
    
    # Display predictions
    st.subheader("📊 Today's Best Bets", divider="red")
    
    if not lines_df.empty and not matches_df.empty:
        predictions = []
        for _, player in lines_df.iterrows():
            match = matches_df[
                (matches_df['team1'] == player['team']) | 
                (matches_df['team2'] == player['team'])
            ].iloc[0]
            
            opponent = match['team2'] if match['team1'] == player['team'] else match['team1']
            analysis = analyze_matchup(player, opponent)
            
            predictions.append({
                'Player': player['player'],
                'Team': player['team'],
                'Line': player['line'],
                'Predicted': analysis['predicted_kills'],
                'Verdict': analysis['over_under'],
                'Confidence': analysis['confidence'],
                'Matchup': f"vs {opponent}",
                'Event': match['event'],
                'Time': match['time']
            })
        
        st.dataframe(
            pd.DataFrame(predictions).style.applymap(
                lambda x: "background-color: #4CAF50" if x == "OVER" else "background-color: #F44336",
                subset=['Verdict']
            ),
            use_container_width=True
        )
    else:
        st.warning("Couldn't load live data - please try again later")
    
    # Chatbot interface
    st.sidebar.header("🤖 Esports Analyst Bot")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.sidebar.chat_message(message["role"]):
            st.sidebar.markdown(message["content"])
    
    if prompt := st.sidebar.chat_input("Ask about player lines or matchups"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        if "analyze" in prompt.lower() and any(p.lower() in prompt.lower() for p in lines_df['player'].tolist()):
            player = next(p for p in lines_df['player'].tolist() if p.lower() in prompt.lower())
            response = analyst.analyze_line(player, lines_df, matches_df)
        else:
            response = "I can analyze player lines and matchups. Try: 'Analyze TenZ' or 'Show Sentinels predictions'"
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.sidebar.rerun()

if __name__ == "__main__":
    main()
