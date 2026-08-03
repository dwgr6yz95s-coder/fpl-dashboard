import requests
import streamlit as st

def get_data(url):
    try:
        response = requests.get(url, timeout=12)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

@st.cache_data(ttl=300)
def load_bootstrap():
    return get_data("https://fantasy.premierleague.com/api/bootstrap-static/")

@st.cache_data(ttl=300)
def load_entry(team_id):
    return get_data(f"https://fantasy.premierleague.com/api/entry/{team_id}/")

@st.cache_data(ttl=300)
def load_fixtures():
    return get_data("https://fantasy.premierleague.com/api/fixtures/")

@st.cache_data(ttl=300)
def load_history(team_id):
    return get_data(f"https://fantasy.premierleague.com/api/entry/{team_id}/history/")

@st.cache_data(ttl=300)
def load_element_summary(player_id):
    return get_data(f"https://fantasy.premierleague.com/api/element-summary/{player_id}/")

@st.cache_data(ttl=300)
def load_league_standings(league_id):
    return get_data(f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/")

@st.cache_data(ttl=300)
def load_dream_team(gw):
    return get_data(f"https://fantasy.premierleague.com/api/dream-team/{gw}/")
