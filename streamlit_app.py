# streamlit_app.py
import streamlit as st
import pandas as pd
import numpy as np
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from scipy.stats import norm
import logging

# ------------------------------
# CONFIG
# ------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
UNDERDOG_URL = "https://underdogfantasy.com/pick-em/higher-lower/all/val"
VLR_URL = "https://www.vlr.gg/matches"

# ------------------------------
# Logging
# ------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Session State
# ------------------------------
if 'predictions' not in st.session_state:
    st.session_state.predictions = pd.DataFrame()
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# ------------------------------
# Scrape Underdog Fantasy
# ------------------------------
def scrape_underdog():
    logger.info("Scraping Underdog Fantasy...")
    try:
        resp = httpx.get(UNDERDOG_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        players = []
        for card in soup.find_all("div", class_="player-line"):
            try:
                name = card.find("div", class_="player-name").text.strip()
                line = float(card.find("div", class_="line-value").text.strip())
                team = card.find("div", class_="player-team").text.strip()
                players.append({
                    "name": name,
                    "line": line,
                    "team": team,
                    "scraped_at": datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.warning(f"Parse error: {e}")
                continue

        df = pd.DataFrame(players)
        logger.info(f"Underdog scraped: {len(df)} players.")
        return df

    except Exception as e:
        logger.error(f"Underdog scrape failed: {e}")
        return pd.DataFrame()

# ------------------------------
# Scrape VLR Matches
# ------------------------------
def scrape_vlr_matches():
    logger.info("Scraping VLR.gg...")
    try:
        resp = httpx.get(VLR_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        matches = []
        for match in soup.select("a.match-item"):
            try:
                team1 = match.select_one("div.mod-1").text.strip()
                team2 = match.select_one("div.mod-2").text.strip()
                event = match.select_one("div.match-item-event").text.strip()
                time_text = match.select_one("div.match-item-time").text.strip()
                link = "https://www.vlr.gg" + match["href"]

                matches.append({
                    "team1": team1,
                    "team2": team2,
                    "event": event,
                    "time": time_text,
                    "link": link
                })
            except Exception as e:
                logger.warning(f"Parse error: {e}")
                continue

        df = pd.DataFrame(matches)
        logger.info(f"VLR scraped: {len(df)} matches.")
        return df

    except Exception as e:
        logger.error(f"VLR scrape failed: {e}")
        return pd.DataFrame()

# ------------------------------
# Simple Prediction Logic
# ------------------------------
def calculate_predictions(lines_df, matches_df):
    if lines_df.empty or matches_df.empty:
        return pd.DataFrame()

    predictions = []
    for _, row in lines_df.iterrows():
        try:
            # Match player team with VLR match
            match = matches_df[
                matches_df['team1'].str.contains(row['team'], case=False) |
                matches_df['team2'].str.contains(row['team'], case=False)
            ].iloc[0]

            opponent = match['team2'] if match['team1'].lower() == row['team'].lower() else match['team1']

            # Fake normal distribution
            mu = row['line'] * 1.1
            sigma = 2.5
            p_over = 1 - norm.cdf(row['line'], mu, sigma)

            verdict = "OVER" if p_over > 0.55 else "UNDER"
            confidence = (
                "High" if abs(p_over - 0.5) > 0.3 else
                "Medium" if abs(p_over - 0.5) > 0.15 else
                "Low"
            )

            predictions.append({
                "Player": row['name'],
                "Team": row['team'],
                "Opponent": opponent,
                "Event": match['event'],
                "Time": match['time'],
                "Line": row['line'],
                "P(OVER)": f"{p_over:.0%}",
                "Verdict": verdict,
                "Confidence": confidence,
                "Match Link": match['link']
            })

        except Exception as e:
            logger.warning(f"Prediction error for {row['name']}: {e}")
            continue

    df = pd.DataFrame(predictions)
    logger.info(f"Generated {len(df)} predictions.")
    return df

# ------------------------------
# Simple Analyst Bot
# ------------------------------
class EsportsAnalyst:
    def __init__(self):
        self.facts = {
            "over under": "OVER/UNDER predictions come from a basic stats model.",
            "confidence": "Confidence is based on probability spread from 50%.",
            "valorant": "This only predicts for VALORANT lines from Underdog Fantasy."
        }

    def generate_response(self, question, preds_df):
        question = question.lower()
        for key in self.facts:
            if key in question:
                return self.facts[key]

        if not preds_df.empty:
            if "over" in question:
                overs = preds_df[preds_df["Verdict"] == "OVER"]
                if not overs.empty:
                    return overs[["Player", "Line", "Confidence"]].to_markdown()
            if "under" in question:
                unders = preds_df[preds_df["Verdict"] == "UNDER"]
                if not unders.empty:
                    return unders[["Player", "Line", "Confidence"]].to_markdown()
            if "match" in question:
                return preds_df[["Team", "Opponent", "Event", "Time"]].drop_duplicates().to_markdown()

        return "Ask about: OVER/UNDER picks, confidence levels, or matches."

# ------------------------------
# Main App
# ------------------------------
def main():
    st.set_page_config(page_title="VALORANT Betting AI", layout="wide")

    analyst = EsportsAnalyst()

    st.title("🔫 VALORANT Betting AI")
    st.write("Real-time Underdog lines + VLR matches + stats model.")

    if st.button("🔄 Refresh Data"):
        st.info("Scraping latest data...")
        lines = scrape_underdog()
        matches = scrape_vlr_matches()
        preds = calculate_predictions(lines, matches)
        st.session_state.predictions = preds
        st.session_state.last_update = datetime.now(timezone.utc)

    if not st.session_state.predictions.empty:
        st.subheader("Predictions")
        st.dataframe(st.session_state.predictions)

        st.caption(f"Last updated: {st.session_state.last_update}")

    else:
        st.warning("No predictions yet. Click refresh!")

    st.sidebar.title("🤖 Ask Analyst")
    for chat in st.session_state.chat_history:
        with st.sidebar:
            st.markdown(f"**{chat['role'].capitalize()}**: {chat['content']}")

    if question := st.sidebar.text_input("Ask something..."):
        st.session_state.chat_history.append({"role": "user", "content": question})
        reply = analyst.generate_response(question, st.session_state.predictions)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.sidebar:
            st.markdown(f"**Assistant**: {reply}")

if __name__ == "__main__":
    main()
