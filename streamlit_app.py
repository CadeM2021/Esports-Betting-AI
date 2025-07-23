def calculate_value_bets(players_df, matches_df):
    """Identify best bets for upcoming matches"""
    try:
        # Merge with upcoming matches
        merged = pd.merge(
            players_df,
            matches_df,
            how="cross"
        )
        
        # Filter players actually in these matches - FIXED THIS SECTION
        merged = merged[
            merged.apply(lambda x: (
                str(x['name']) in str(x['team1']) or 
                str(x['name']) in str(x['team2'])
            ), axis=1)
        ]  # THIS CLOSES THE BRACKET PROPERLY
        
        # Calculate expected value
        merged["value_score"] = merged["edge"] * merged["count"]
        merged["bet_confidence"] = pd.cut(
            merged["count"],
            bins=[0, 3, 7, 20],
            labels=["Low", "Medium", "High"]
        )
        
        return merged.sort_values(["value_score", "edge"], ascending=False)
    except Exception as e:
        st.error(f"Analysis error: {str(e)}")
        return pd.DataFrame()
