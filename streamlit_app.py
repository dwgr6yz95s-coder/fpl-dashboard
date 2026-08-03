import streamlit as st
from collections import defaultdict

from api import (
    load_bootstrap, load_entry, load_fixtures,
    load_history, load_element_summary,
    load_league_standings, load_dream_team
)
from helpers import is_valid_formation, make_row

st.set_page_config(
    page_title="FPL Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stMetric { background-color: #21262d; padding: 12px 16px; border-radius: 10px; }
    h1 { font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
st.sidebar.markdown("### ⚙️ Settings")
default_id = 570479

team_id_input = st.sidebar.text_input(
    "FPL Team ID",
    value=str(st.session_state.get("team_id", default_id)),
    help="Find it in your FPL URL: fantasy.premierleague.com/entry/XXXXXXX/"
)

try:
    TEAM_ID = int(team_id_input.strip())
    st.session_state["team_id"] = TEAM_ID
except:
    TEAM_ID = default_id
    st.sidebar.error("Enter a valid number")

st.sidebar.caption("Enter any Team ID to view that manager's data.")
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "Home",
        "Manager Info",
        "Manager History",
        "Gameweek Info",
        "Squad",
        "Mini-Leagues",
        "Fixtures",
        "Fixture Difficulty",
        "Players - Easiest Fixtures",
        "Player Detail",
        "Dream Team",
        "Transfer Suggestions"
    ],
    label_visibility="collapsed"
)

# ---------- LOAD DATA ----------
bootstrap = load_bootstrap()
entry = load_entry(TEAM_ID)
fixtures = load_fixtures()

team_name = entry.get("name", "FPL Manager") if entry else "FPL Manager"
st.title(f"⚽ {team_name}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Team Rating", "88%")
col2.metric("Predicted", "60 pts")
col3.metric("In the Bank", "£0.0m")
col4.metric("Transfers", "0/∞")

st.divider()

# ---------- PAGES ----------
if page == "Home":
    st.subheader("Dashboard Overview")
    if bootstrap:
        next_gw = None
        for event in bootstrap.get("events", []):
            if event.get("is_next"):
                next_gw = event
                break
        if next_gw:
            deadline = next_gw.get('deadline_time', 'N/A')[:16].replace('T', ' ')
            st.info(f"**Next Gameweek:** {next_gw['id']} – {next_gw['name']}  \n**Deadline:** {deadline}")
    st.write("Use the sidebar to explore different sections of your FPL data.")

elif page == "Manager Info":
    st.subheader("Manager Info")
    if entry:
        st.write(f"**Team name:** {entry.get('name', 'N/A')}")
        st.write(f"**Manager:** {entry.get('player_first_name', '')} {entry.get('player_last_name', '')}")
        points = entry.get('summary_overall_points')
        rank = entry.get('summary_overall_rank')
        c1, c2 = st.columns(2)
        c1.metric("Overall Points", points if points is
