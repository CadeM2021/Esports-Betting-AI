# VALORANT PROPS LAB ULTIMATE
import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import plotly.express as px
from scipy.stats import norm
import openai
import time
import re

# ------------------------------
# CONFIGURATION
# ------------------------------
st.set_page_config(
    page_title="VALORANT PROPS LAB ULTIMATE",
    page_icon="🔫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    :root {
        --primary: #6E40C9;
        --secondary: #4A90E2;
        --dark: #0E1117;
        --darker: #1A1D24;
        --card: #1E222A;
    }
    .main {
        background-color: var(--dark);
        color: white;
    }
    .sidebar .sidebar-content {
        background-color: var(--darker);
    }
    .player-card {
        background-color: var(--card);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid var(--primary);
        transition: transform 0.2s;
    }
    .player-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .match-card {
        background-color: var(--card);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 25px;
        border-left: 4px solid var(--secondary);
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary) !important;
        color: white !important;
    }
    .stButton>button {
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        color: white;
        border: none;
        border-radius: 5px;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .stTextInput>div>div>input {
        background-color: var(--card);
        color: white;
    }
    .stSelectbox>div>div>select {
        background-color: var(--card);
        color: white;
    }
    .stDataFrame {
        background-color: var(--card) !important;
        border-radius: 10px !important;
    }
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--darker);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--primary);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--secondary);
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------
# DATA SERVICES
# ------------------------------
class ValorantDataService:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        self.cache = {}
        self.base_url = "https://www.vlr.gg"

    def get_match_data(self, vlr_url):
        """Extract detailed match data from VLR.gg"""
        try:
            if vlr_url in self.cache:
                return self.cache[vlr_url]

            response = requests.get(vlr_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract match info
            match_info = {
                'teams': [],
                'players': [],
                'maps': [],
                'time': soup.select_one('.match-header-date').text.strip(),
                'event': soup.select_one('.match-header-event').text.strip(),
                'url': vlr_url
            }

            # Get team data
            for team in soup.select('.match-header-link'):
                match_info['teams'].append({
                    'name': team.select_one('.wf-title-med').text.strip(),
                    'score': team.select_one('.score').text.strip(),
                    'logo': team.select_one('.team-logo img')['src']
                })

            # Get player stats from all maps
            for map_div in soup.select('.vm-stats-game'):
                map_name = map_div.select_one('.map-name')['data-game-id']
                for team_div in map_div.select('.team'):
                    team_name = team_div.select_one('.team-name').text.strip()
                    for row in team_div.select('tr')[1:]:  # Skip header
                        cols = row.select('td')
                        player_data = {
                            'name': cols[0].select_one('.text-of').text.strip(),
                            'team': team_name,
                            'kills': float(cols[2].text.strip()),
                            'deaths': float(cols[3].text.strip()),
                            'acs': float(cols[8].text.strip()),
                            'agent': cols[1].select_one('img')['title'],
                            'map': map_name
                        }
                        # Add headshot percentage if available
                        if len(cols) > 9:
                            player_data['hs_percent'] = float(cols[9].text.strip('%'))
                        match_info['players'].append(player_data)

            # Get map data
            for map_div in soup.select('.map'):
                map_data = {
                    'name': map_div.select_one('.map-name').text.strip(),
                    'score': map_div.select_one('.map-score').text.strip(),
                    'winner': map_div.select_one('.mod-win')['class'][1].split('-')[1] if map_div.select_one('.mod-win') else None
                }
                match_info['maps'].append(map_data)

            self.cache[vlr_url] = match_info
            return match_info

        except Exception as e:
            st.error(f"Error scraping VLR.gg: {str(e)}")
            return None

    def get_player_history(self, player_name, team_name):
        """Get historical player data from VLR.gg profile"""
        try:
            # Search for player profile
            search_url = f"{self.base_url}/search?q={player_name.replace(' ', '+')}"
            response = requests.get(search_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find matching player profile
            profile_link = None
            for result in soup.select('.search-item'):
                if team_name.lower() in result.text.lower() and player_name.lower() in result.text.lower():
                    profile_link = result.find('a')['href']
                    break
            
            if not profile_link:
                return None
                
            # Scrape player profile
            profile_url = f"{self.base_url}{profile_link}"
            profile_response = requests.get(profile_url, headers=self.headers)
            profile_soup = BeautifulSoup(profile_response.text, 'html.parser')
            
            # Extract recent matches
            recent_matches = []
            for row in profile_soup.select('.wf-table-inset.mod-overview tr')[1:11]:  # Last 10 matches
                cols = row.select('td')
                recent_matches.append({
                    'date': cols[0].text.strip(),
                    'kills': float(cols[2].text.strip()),
                    'deaths': float(cols[3].text.strip()),
                    'acs': float(cols[8].text.strip()),
                    'agent': cols[1].select_one('img')['title'] if cols[1].select_one('img') else None
                })
            
            # Calculate stats
            kills = [m['kills'] for m in recent_matches]
            avg_kills = np.mean(kills) if kills else 0
            kill_std = np.std(kills) if kills else 0
            last_5_avg = np.mean(kills[:5]) if len(kills) >= 5 else avg_kills
            
            # Determine primary role
            role_counts = {}
            for m in recent_matches:
                if m['agent']:
                    role = self._agent_to_role(m['agent'])
                    role_counts[role] = role_counts.get(role, 0) + 1
            primary_role = max(role_counts.items(), key=lambda x: x[1])[0] if role_counts else "Flex"
            
            return {
                'avg_kills': round(avg_kills, 1),
                'kill_std': round(kill_std, 1),
                'last_5_avg': round(last_5_avg, 1),
                'last_5_kills': kills[:5],
                'primary_role': primary_role,
                'recent_matches': recent_matches,
                'matches_analyzed': len(recent_matches)
            }
            
        except Exception as e:
            st.warning(f"Couldn't get full history for {player_name}: {str(e)}")
            return None

    def _agent_to_role(self, agent_name):
        """Map agent name to role"""
        agent_name = agent_name.lower()
        if any(a in agent_name for a in ['jett', 'phoenix', 'raze', 'reyna', 'neon', 'yoru']):
            return "Duelist"
        elif any(a in agent_name for a in ['sova', 'breach', 'kayo', 'skye', 'fade', 'gekko']):
            return "Initiator"
        elif any(a in agent_name for a in ['omen', 'viper', 'brimstone', 'astra', 'harbor']):
            return "Controller"
        elif any(a in agent_name for a in ['sage', 'killjoy', 'cypher', 'chamber', 'deadlock']):
            return "Sentinel"
        return "Flex"

# ------------------------------
# PREDICTION ENGINE
# ------------------------------
class AdvancedPredictionModel:
    def __init__(self):
        self.position_factors = {
            "Duelist": {"kill_mod": 1.15, "sigma": 3.5},
            "Initiator": {"kill_mod": 1.05, "sigma": 3.0},
            "Controller": {"kill_mod": 0.95, "sigma": 2.5},
            "Sentinel": {"kill_mod": 0.90, "sigma": 2.0},
            "Flex": {"kill_mod": 1.00, "sigma": 3.0}
        }
        
        # Team strength ratings (can be updated dynamically)
        self.team_ratings = {
            "Team Liquid": 1.15,
            "Fnatic": 1.10,
            "DRX": 1.08,
            "LOUD": 1.05,
            "Optic Gaming": 1.03,
            "Default": 1.00
        }

    def predict_player_line(self, player_data, match_context):
        """Generate advanced predictions for a player"""
        try:
            # Determine position from agent or history
            position = player_data.get('position', 'Flex')
            if 'agent' in player_data:
                position = data_service._agent_to_role(player_data['agent'])
            
            pos_data = self.position_factors.get(position, self.position_factors["Flex"])

            # Get historical data
            history = data_service.get_player_history(player_data['name'], player_data['team']) or {
                'avg_kills': player_data.get('kills', 20),
                'kill_std': 3.0,
                'last_5_avg': player_data.get('kills', 20),
                'primary_role': position
            }
            
            # Calculate weighted average (recent matches weighted more)
            recent_weight = 0.7 if history.get('matches_analyzed', 0) >= 5 else 0.5
            historical_weight = 1 - recent_weight
            weighted_avg = (history['last_5_avg'] * recent_weight + 
                          history['avg_kills'] * historical_weight)
            
            # Adjust for position
            adjusted_mu = weighted_avg * pos_data["kill_mod"]
            
            # Adjust for opponent strength
            opponent = match_context['opponent']
            opponent_strength = self.team_ratings.get(
                next((k for k in self.team_ratings if k in opponent), 
                self.team_ratings["Default"])
            team_strength = self.team_ratings.get(
                next((k for k in self.team_ratings if k in player_data['team']), 
                self.team_ratings["Default"])
            strength_ratio = opponent_strength / team_strength
            matchup_factor = 1 + (1 - strength_ratio) * 0.15
            final_mu = adjusted_mu * matchup_factor
            
            # Dynamic sigma based on consistency and matchup
            consistency_factor = history['kill_std'] / history['avg_kills'] if history['avg_kills'] > 0 else 1.0
            matchup_volatility = 1.2 if strength_ratio < 0.9 or strength_ratio > 1.1 else 1.0
            sigma = pos_data["sigma"] * consistency_factor * matchup_volatility
            
            # Calculate probabilities
            line = final_mu  # Could be adjusted to match betting lines
            p_over = 1 - norm.cdf(line, final_mu, sigma)
            edge = p_over - 0.5
            confidence = min(3, max(1, int(abs(edge) * 12)))  # More sensitive confidence
            
            return {
                "Player": player_data['name'],
                "Team": player_data['team'],
                "Position": position,
                "Agent": player_data.get('agent', 'Unknown'),
                "Line": round(line, 1),
                "P(OVER)": p_over,
                "Edge": edge,
                "Confidence": "⭐" * confidence,
                "μ": round(final_mu, 1),
                "σ": round(sigma, 1),
                "History": history,
                "Matchup": f"{player_data['team']} vs {opponent}",
                "Last5": history.get('last_5_kills', []),
                "HS%": player_data.get('hs_percent', history.get('hs_percent', 0))
            }

        except Exception as e:
            st.error(f"Prediction error for {player_data.get('name', 'Unknown')}: {str(e)}")
            return None

# ------------------------------
# AI ANALYST
# ------------------------------
class ValorantAnalyst:
    def __init__(self):
        self.knowledge_base = {
            "model": """
            **Our Prediction Model Considers:**
            - **Recent Performance** (70% weight for last 5 matches)
            - **Career Averages** (30% weight)
            - **Position Adjustments**:
              - Duelists: +15% expected kills
              - Initiators: +5%
              - Controllers: -5%
              - Sentinels: -10%
            - **Opponent Strength**: Adjusted based on team rankings
            - **Performance Consistency**: Higher volatility for inconsistent players
            """,
            "confidence": """
            **Confidence Ratings:**
            - ⭐ = 50-62% certainty
            - ⭐⭐ = 62-75%
            - ⭐⭐⭐ = 75%+
            """,
            "help": """
            **Ask me about:**
            - Player predictions (e.g. "How will Player1 perform?")
            - Team matchups (e.g. "How does Team A match up against Team B?")
            - Model details (e.g. "How does the model work?")
            - Betting strategies (e.g. "What's the best bet this match?")
            """
        }

    def generate_analysis(self, player_data):
        """Generate detailed AI analysis for a player"""
        analysis = f"""
        ### 🎯 **{player_data['Player']}** ({player_data['Team']})  
        **{player_data['Position']}** playing **{player_data['Agent']}**  
        
        📊 **Projected Stats:**  
        - **Kill Line:** {player_data['Line']}  
        - **Over Probability:** {player_data['P(OVER)']:.0%}  
        - **Confidence:** {player_data['Confidence']}  
        - **Expected Range:** {player_data['μ']:.1f} ± {player_data['σ']:.1f} kills  
        
        📈 **Recent Form:**  
        - Last 5 kills: {', '.join(map(str, player_data['Last5']))}  
        - HS%: {player_data.get('HS%', 'N/A')}%  
        - Avg kills (last 5): {np.mean(player_data['Last5']):.1f}  
        
        🔍 **Matchup:**  
        {player_data['Matchup']}  
        
        💡 **Recommendation:** {'✅ **OVER**' if player_data['P(OVER)'] > 0.55 else '❌ **UNDER**'}  
        """
        
        # Add contextual tips
        if player_data['P(OVER)'] > 0.6:
            analysis += "\n🌟 **Tip:** Strong OVER value based on recent form and matchup"
        elif player_data['P(OVER)'] < 0.4:
            analysis += "\n⚠️ **Warning:** Player underperforming recently, consider UNDER"
        
        if player_data.get('HS%', 0) > 25:
            analysis += f"\n🎯 **Headshot Specialist:** High HS% of {player_data['HS%']}% increases kill potential"
        
        return analysis.strip()

    def generate_match_analysis(self, match_data):
        """Generate analysis for the entire match"""
        team1, team2 = match_data['teams'][0], match_data['teams'][1]
        
        analysis = f"""
        ## 🏆 **{team1['name']} vs {team2['name']}**  
        **{match_data['event']}** • {match_data['time']}  
        
        ### 📊 Match Overview:
        - **Maps:** {', '.join(m['name'] for m in match_data['maps'])}  
        - **Recent Form:** (Add team form analysis here)  
        
        ### 🔍 Key Matchup Factors:
        1. **Duelist Showdown:** Compare Jett/Raze players  
        2. **Controller Play:** Map control differences  
        3. **Head-to-Head History:** Past match results  
        
        ### 💎 Best Value Bets:
        1. *(Add generated betting tips here)*  
        2. *(Based on player projections)*  
        3. *(And matchup factors)*  
        """
        return analysis

# ------------------------------
# UI COMPONENTS
# ------------------------------
def render_player_card(player_data):
    """Modern interactive player card with stats"""
    with st.container():
        # Card header with gradient border
        st.markdown(f"""
        <div class="player-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px">
                <div>
                    <h3 style="margin:0">{player_data['Player']}</h3>
                    <p style="margin:0; color:#AAAAAA">{player_data['Team']}</p>
                </div>
                <div style="background:{'#4CAF50' if player_data['P(OVER)'] > 0.5 else '#F44336'}; 
                             padding:2px 10px; border-radius:12px;">
                    <small style="color:white">{'OVER' if player_data['P(OVER)'] > 0.5 else 'UNDER'}</small>
                </div>
            </div>
            
            <div style="display:flex; justify-content:space-between; margin:5px 0">
                <div>
                    <small>POSITION</small>
                    <p style="margin:0; font-weight:bold">{player_data['Position']}</p>
                </div>
                <div>
                    <small>AGENT</small>
                    <p style="margin:0; font-weight:bold">{player_data['Agent']}</p>
                </div>
            </div>
            
            <div style="display:flex; justify-content:space-between; margin:10px 0; text-align:center">
                <div>
                    <small>PROJECTED</small>
                    <h2 style="margin:0; color:white">{player_data['Line']}</h2>
                </div>
                <div>
                    <small>OVER %</small>
                    <h2 style="margin:0; color:{'#4CAF50' if player_data['P(OVER)'] > 0.5 else '#F44336'}">
                        {player_data['P(OVER)']:.0%}
                    </h2>
                </div>
                <div>
                    <small>CONFIDENCE</small>
                    <h2 style="margin:0; color:#FFD700">{player_data['Confidence']}</h2>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Kill distribution chart with line marker
        fig = px.histogram(
            x=np.random.normal(player_data['μ'], player_data['σ'], 1000),
            nbins=20,
            range_x=[max(0, player_data['μ']-3*player_data['σ']), player_data['μ']+3*player_data['σ']],
            color_discrete_sequence=['#6E40C9']
        )
        fig.add_vline(
            x=player_data['Line'], 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Line: {player_data['Line']}", 
            annotation_position="top right"
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(t=0, b=0, l=0, r=0),
            height=150,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

        # AI Analysis expander
        with st.expander("🤖 AI Analysis", expanded=False):
            st.markdown(analyst.generate_analysis(player_data))

def render_match_header(match_data):
    """Match information header card"""
    team1, team2 = match_data['teams'][0], match_data['teams'][1]
    
    with st.container():
        st.markdown(f"""
        <div class="match-card">
            <div style="display:flex; justify-content:space-between; align-items:center">
                <div>
                    <h2 style="margin:0">{team1['name']} vs {team2['name']}</h2>
                    <p style="margin:0; color:#AAAAAA">{match_data['event']} • {match_data['time']}</p>
                </div>
                <a href="{match_data['url']}" target="_blank" style="text-decoration:none">
                    <button style="background:#6E40C9; color:white; border:none; padding:5px 10px; border-radius:5px">
                        View on VLR.gg
                    </button>
                </a>
            </div>
            
            <div style="display:flex; justify-content:space-around; margin:15px 0">
                <div style="text-align:center">
                    <img src="{team1['logo']}" width="60" style="border-radius:50%">
                    <h1 style="margin:5px 0">{team1['score']}</h1>
                </div>
                <div style="text-align:center; margin:auto 0">
                    <h2 style="margin:0">VS</h2>
                </div>
                <div style="text-align:center">
                    <img src="{team2['logo']}" width="60" style="border-radius:50%">
                    <h1 style="margin:5px 0">{team2['score']}</h1>
                </div>
            </div>
            
            <div style="display:flex; justify-content:center; gap:10px">
                {''.join([f"<span style='background:#2E4053; padding:2px 8px; border-radius:4px'>{m['name']} {m['score']}</span>" for m in match_data['maps']])}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------
# MAIN APPLICATION
# ------------------------------
# Initialize services
data_service = ValorantDataService()
prediction_model = AdvancedPredictionModel()
analyst = ValorantAnalyst()

# Session state management
if 'current_match' not in st.session_state:
    st.session_state.current_match = None
if 'predictions' not in st.session_state:
    st.session_state.predictions = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'show_help' not in st.session_state:
    st.session_state.show_help = False

# Sidebar - Data Input
with st.sidebar:
    st.title("🔫 VALORANT PROPS LAB")
    
    # Match URL input
    st.subheader("Match Data Input")
    vlr_url = st.text_input(
        "Enter VLR.gg Match URL:",
        placeholder="https://www.vlr.gg/12345/team1-vs-team2",
        key="match_url_input"
    )
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Analyze Match", type="primary"):
            if vlr_url:
                with st.spinner("Loading match data..."):
                    match_data = data_service.get_match_data(vlr_url)
                    if match_data:
                        st.session_state.current_match = match_data
                        st.session_state.predictions = []
                        
                        # Generate predictions for all players
                        for player in match_data['players']:
                            opponent = next(
                                (t['name'] for t in match_data['teams'] 
                                if t['name'] != player['team']),
                                "Unknown"
                            )
                            context = {'opponent': opponent}
                            prediction = prediction_model.predict_player_line(player, context)
                            if prediction:
                                st.session_state.predictions.append(prediction)
                        
                        st.success(f"Analyzed {len(st.session_state.predictions)} players!")
                    else:
                        st.error("Could not load match data")
            else:
                st.warning("Please enter a VLR.gg URL")
    
    with col2:
        if st.button("Load Sample Data"):
            sample_match = {
                'teams': [
                    {'name': 'Team Liquid', 'score': '2', 'logo': 'https://www.vlr.gg/img/vlr/tmp/vlr.png'},
                    {'name': 'Fnatic', 'score': '1', 'logo': 'https://www.vlr.gg/img/vlr/tmp/vlr.png'}
                ],
                'players': [
                    {'name': 'Jawgemo', 'team': 'Team Liquid', 'kills': 23, 'deaths': 18, 'acs': 245, 'agent': 'Jett'},
                    {'name': 'Derke', 'team': 'Fnatic', 'kills': 27, 'deaths': 20, 'acs': 265, 'agent': 'Raze'},
                    {'name': 'Boaster', 'team': 'Fnatic', 'kills': 15, 'deaths': 22, 'acs': 180, 'agent': 'Brimstone'}
                ],
                'maps': [{'name': 'Ascent', 'score': '13-11'}, {'name': 'Bind', 'score': '9-13'}],
                'time': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'event': 'VCT 2023',
                'url': 'https://www.vlr.gg/12345'
            }
            st.session_state.current_match = sample_match
            st.session_state.predictions = []
            
            for player in sample_match['players']:
                opponent = next(t['name'] for t in sample_match['teams'] if t['name'] != player['team'])
                context = {'opponent': opponent}
                prediction = prediction_model.predict_player_line(player, context)
                if prediction:
                    st.session_state.predictions.append(prediction)
            
            st.success("Sample data loaded!")

    # Underdog lines input
    st.subheader("Underdog Lines Input")
    underdog_json = st.text_area(
        "Paste Underdog Lines JSON:",
        height=150,
        help="Paste player props data from Underdog in JSON format",
        key="underdog_input"
    )
    
    if st.button("Process Underdog Data"):
        if underdog_json:
            try:
                data = json.loads(underdog_json)
                match_data = {
                    'teams': [
                        {'name': data.get('team1', 'Team A'), 'score': '?', 'logo': ''},
                        {'name': data.get('team2', 'Team B'), 'score': '?', 'logo': ''}
                    ],
                    'players': [],
                    'maps': [],
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'event': 'Custom Underdog Match',
                    'url': ''
                }
                
                # Convert Underdog format to our player data format
                for player in data.get('players', []):
                    match_data['players'].append({
                        'name': player.get('name', 'Unknown'),
                        'team': player.get('team', 'Unknown'),
                        'kills': float(player.get('line', 20)),
                        'deaths': 0,
                        'acs': 0,
                        'agent': player.get('agent', 'Unknown')
                    })
                
                st.session_state.current_match = match_data
                st.session_state.predictions = []
                
                for player in match_data['players']:
                    opponent = next(t['name'] for t in match_data['teams'] if t['name'] != player['team'])
                    context = {'opponent': opponent}
                    prediction = prediction_model.predict_player_line(player, context)
                    if prediction:
                        st.session_state.predictions.append(prediction)
                
                st.success(f"Processed {len(st.session_state.predictions)} players from Underdog!")
            except Exception as e:
                st.error(f"Error parsing Underdog data: {str(e)}")
        else:
            st.warning("Please paste Underdog JSON data")

    # Help section
    st.markdown("---")
    if st.button("Help & Instructions"):
        st.session_state.show_help = not st.session_state.show_help
    
    if st.session_state.show_help:
        st.markdown("""
        **How to Use:**
        1. Paste a VLR.gg match URL or Underdog JSON
        2. Click "Analyze Match" or "Process Underdog Data"
        3. View player projections and betting insights
        
        **Data Sources:**
        - VLR.gg for match data
        - Underdog for betting lines
        - Historical stats from player profiles
        
        **Features:**
        - Player kill projections
        - Over/under probabilities
        - AI-powered analysis
        - Matchup insights
        """)

# Main Content Area
if st.session_state.current_match:
    # Match Header
    render_match_header(st.session_state.current_match)
    
    # Match Analysis from AI
    with st.expander("📝 Match Analysis Report", expanded=True):
        st.markdown(analyst.generate_match_analysis(st.session_state.current_match))
    
    # Player Projections
    st.subheader("📊 Player Projections")
    
    # Filters
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            team_filter = st.selectbox(
                "Team",
                ["All"] + list(sorted(set(p['Team'] for p in st.session_state.predictions)),
                key="team_filter"
            )
        with col2:
            position_filter = st.selectbox(
                "Position",
                ["All"] + list(sorted(set(p['Position'] for p in st.session_state.predictions)),
                key="position_filter"
            )
        with col3:
            confidence_filter = st.selectbox(
                "Confidence",
                ["All", "High (⭐⭐⭐)", "Medium (⭐⭐)", "Low (⭐)"],
                key="confidence_filter"
            )
        with col4:
            sort_by = st.selectbox(
                "Sort By",
                ["Edge", "P(OVER)", "Line", "Team"],
                key="sort_by"
            )
    
    # Filter and sort predictions
    filtered = st.session_state.predictions
    if team_filter != "All":
        filtered = [p for p in filtered if p['Team'] == team_filter]
    if position_filter != "All":
        filtered = [p for p in filtered if p['Position'] == position_filter]
    if confidence_filter != "All":
        min_stars = len(confidence_filter.split("(")[1]) - 1
        filtered = [p for p in filtered if len(p['Confidence']) >= min_stars]
    
    # Sort based on selection
    reverse_sort = True if sort_by in ["Edge", "P(OVER)"] else False
    filtered.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse_sort)
    
    # Display player cards in responsive grid
    cols = st.columns(4)
    for idx, player in enumerate(filtered):
        with cols[idx % 4]:
            render_player_card(player)
    
    # Props Lab Optimizer
    st.subheader("🔥 Props Lab Optimizer")
    if filtered:
        df = pd.DataFrame(filtered)
        
        # Calculate value bets
        df['Value'] = df['Edge'].apply(lambda x: "⭐" * min(3, max(1, int(x * 10 + 1))))
        df['Bet'] = df['P(OVER)'].apply(lambda x: "OVER" if x > 0.55 else "UNDER")
        
        st.dataframe(
            df[['Player', 'Team', 'Position', 'Line', 'P(OVER)', 'Edge', 'Value', 'Bet']],
            column_config={
                "P(OVER)": st.column_config.ProgressColumn(
                    format="%.0f%%",
                    min_value=0,
                    max_value=1,
                    help="Probability of going over the line"
                ),
                "Edge": st.column_config.NumberColumn(
                    format="+%.2f",
                    help="Expected value edge over market"
                ),
                "Value": st.column_config.TextColumn(
                    "Value",
                    help="Betting value rating"
                )
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download as CSV",
                df.to_csv(index=False),
                "valorant_props.csv",
                "text/csv"
            )
        with col2:
            st.download_button(
                "Download as JSON",
                df.to_json(orient='records'),
                "valorant_props.json",
                "application/json"
            )
    else:
        st.warning("No players match the current filters")
    
    # AI Chat Interface
    st.subheader("💬 AI Analyst Chat")
    
    # Chat container with scrollable history
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                with st.chat_message("user"):
                    st.write(msg['content'])
            else:
                with st.chat_message("assistant"):
                    st.write(msg['content'])
    
    # Chat input
    if prompt := st.chat_input("Ask the analyst..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Generate response
        response = ""
        if any(word in prompt.lower() for word in ["model", "how it works"]):
            response = analyst.knowledge_base["model"]
        elif "confidence" in prompt.lower():
            response = analyst.knowledge_base["confidence"]
        elif "help" in prompt.lower():
            response = analyst.knowledge_base["help"]
        elif any(p['Player'].lower() in prompt.lower() for p in st.session_state.predictions):
            player_name = next(p['Player'] for p in st.session_state.predictions if p['Player'].lower() in prompt.lower())
            player_data = next(p for p in st.session_state.predictions if p['Player'] == player_name)
            response = analyst.generate_analysis(player_data)
        elif st.session_state.current_match and any(t['name'].lower() in prompt.lower() for t in st.session_state.current_match['teams']):
            response = analyst.generate_match_analysis(st.session_state.current_match)
        else:
            response = "I can analyze players, teams, and matchups. Try asking about a specific player or team!"
        
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

else:
    # Welcome screen
    st.title("Welcome to VALORANT PROPS LAB ULTIMATE")
    st.markdown("""
    ### The most advanced VALORANT betting analytics platform
    
    **To get started:**
    1. Paste a VLR.gg match URL in the sidebar
    2. Or paste Underdog lines data in JSON format
    3. Click "Analyze Match" or "Process Underdog Data"
    
    **Features:**
    - Player kill projections with confidence ratings
    - AI-powered analysis for each player
    - Matchup insights and team comparisons
    - Props Lab optimizer for finding value bets
    - Interactive chat with our AI analyst
    
    **Sample VLR.gg URLs:**
    - https://www.vlr.gg/12345/team-liquid-vs-fnatic
    - https://www.vlr.gg/67890/drx-vs-loud
    """)
    
    st.image("https://images.contentstack.io/v3/assets/bltb6530b271fddd0b1/blt29d7c4f6bc077e9a/649bdea2b4a2e36e00e4a186/071123_Valorant_EP6_PlayVALORANT_ContentStackThumbnail_1200x625_MB01.jpg",
             use_column_width=True)

    # Sample Underdog JSON
    with st.expander("Sample Underdog JSON Format"):
        st.code("""
        {
            "team1": "Team Liquid",
            "team2": "Fnatic",
            "players": [
                {
                    "name": "Jawgemo",
                    "team": "Team Liquid",
                    "agent": "Jett",
                    "line": 23.5
                },
                {
                    "name": "Derke",
                    "team": "Fnatic",
                    "agent": "Raze",
                    "line": 25.5
                }
            ]
        }
        """, language="json")

# ------------------------------
# RUN THE APP
# ------------------------------
# streamlit run valorant_props_lab_ultimate.py
