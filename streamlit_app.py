import streamlit as st
import requests
from collections import defaultdict

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

def get_data(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

# Sidebar
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
        "Gameweek Info",
        "Squad",
        "Mini-Leagues",
        "Fixtures",
        "Fixture Difficulty",
        "Players - Easiest Fixtures",
        "Transfer Suggestions"
    ],
    label_visibility="collapsed"
)

@st.cache_data(ttl=300)
def load_bootstrap():
    return get_data("https://fantasy.premierleague.com/api/bootstrap-static/")

@st.cache_data(ttl=300)
def load_entry(team_id):
    return get_data(f"https://fantasy.premierleague.com/api/entry/{team_id}/")

@st.cache_data(ttl=300)
def load_fixtures():
    return get_data("https://fantasy.premierleague.com/api/fixtures/")

def load_squad(team_id):
    """Try to load squad for Gameweek 1 (and next GW as backup)."""
    # First try Gameweek 1
    data = get_data(f"https://fantasy.premierleague.com/api/entry/{team_id}/event/1/picks/")
    if data and "picks" in data and data["picks"]:
        return data

    # Backup: try next gameweek
    bootstrap = load_bootstrap()
    if bootstrap:
        for event in bootstrap.get("events", []):
            if event.get("is_next"):
                data = get_data(f"https://fantasy.premierleague.com/api/entry/{team_id}/event/{event['id']}/picks/")
                if data and "picks" in data and data["picks"]:
                    return data
                break
    return None

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
        c1.metric("Overall Points", points if points is not None else "Not started")
        c2.metric("Overall Rank", f"{rank:,}" if rank is not None else "Not started")
    else:
        st.error("Could not load manager info. Check the Team ID.")

elif page == "Gameweek Info":
    st.subheader("Gameweek Info")
    if bootstrap:
        next_event = None
        for event in bootstrap.get("events", []):
            if event.get("is_next"):
                next_event = event
                break
        if next_event:
            st.write(f"**Next GW:** {next_event['id']} - {next_event['name']}")
            st.write(f"**Deadline:** {next_event.get('deadline_time', 'N/A')}")
        else:
            st.write("No active gameweek yet (pre-season)")
    else:
        st.error("Could not load gameweek info.")

elif page == "Squad":
    st.subheader("Your Squad")
    st.caption("Trying to load your Gameweek 1 team...")

    if not bootstrap:
        st.error("Could not load player data.")
    else:
        squad_data = load_squad(TEAM_ID)

        if not squad_data:
            st.warning(
                "Your squad is not available yet from the official API.\n\n"
                "This is normal in pre-season. The page is ready and will automatically "
                "show your 15 players as soon as the data becomes available "
                "(usually closer to the first deadline or when the season starts)."
            )
        else:
            players = {p["id"]: p for p in bootstrap["elements"]}
            teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
            positions = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

            starters = []
            bench = []

            for pick in squad_data["picks"]:
                p = players.get(pick["element"], {})
                row = {
                    "Pos": positions.get(p.get("element_type"), "?"),
                    "Player": p.get("web_name", "Unknown"),
                    "Team": teams.get(p.get("team"), "?"),
                    "Price": round(p.get("now_cost", 0) / 10, 1),
                    "Status": "C" if pick.get("is_captain") else ("V" if pick.get("is_vice_captain") else "")
                }
                if pick.get("multiplier", 1) == 0:
                    bench.append(row)
                else:
                    starters.append(row)

            st.success("Squad loaded successfully!")
            st.markdown("**Starting XI**")
            st.dataframe(starters, use_container_width=True, hide_index=True)
            st.markdown("**Bench**")
            st.dataframe(bench, use_container_width=True, hide_index=True)

elif page == "Mini-Leagues":
    st.subheader("Mini-Leagues")
    if entry:
        classic = entry.get("leagues", {}).get("classic", [])
        if classic:
            for league in classic:
                st.markdown(f"**{league.get('name')}** — Rank: {league.get('entry_rank', 'N/A')}")
        else:
            st.write("No classic leagues found.")
    else:
        st.error("Could not load leagues.")

elif page == "Fixtures":
    st.subheader("Upcoming Fixtures")
    st.caption("Next 5 gameweeks · FDR: 1 = easiest, 5 = hardest")
    if not bootstrap or not fixtures:
        st.error("Could not load fixtures.")
    else:
        short = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
        next_gws = []
        for event in bootstrap.get("events", []):
            if event.get("is_next") or (next_gws and len(next_gws) < 5):
                next_gws.append(event["id"])
                if len(next_gws) >= 5:
                    break
        if not next_gws:
            next_gws = [1, 2, 3, 4, 5]
        selected = st.selectbox("Select Gameweek", ["All"] + [f"Gameweek {gw}" for gw in next_gws])
        for gw in next_gws:
            if selected != "All" and selected != f"Gameweek {gw}":
                continue
            gw_fixtures = [f for f in fixtures if f.get("event") == gw]
            if not gw_fixtures:
                continue
            st.markdown(f"### Gameweek {gw}")
            rows = []
            for f in sorted(gw_fixtures, key=lambda x: x.get("kickoff_time") or ""):
                kickoff = f.get("kickoff_time")
                if kickoff:
                    try:
                        dt = kickoff.replace("Z", "")
                        kickoff_fmt = dt[8:10] + " " + ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][int(dt[5:7])-1] + " " + dt[11:16]
                    except:
                        kickoff_fmt = kickoff[:16].replace("T", " ")
                else:
                    kickoff_fmt = "TBC"
                rows.append({
                    "Kickoff": kickoff_fmt,
                    "Home": short.get(f["team_h"], "?"),
                    "Away": short.get(f["team_a"], "?"),
                    "Home FDR": f.get("team_h_difficulty", "-"),
                    "Away FDR": f.get("team_a_difficulty", "-")
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

elif page == "Fixture Difficulty":
    st.subheader("Fixture Difficulty (FDR)")
    st.caption("1 = Easiest  ·  5 = Hardest")
    if bootstrap and fixtures:
        teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
        next_gws = []
        for event in bootstrap.get("events", []):
            if event.get("is_next") or (next_gws and len(next_gws) < 5):
                next_gws.append(event["id"])
                if len(next_gws) >= 5:
                    break
        if not next_gws:
            next_gws = [1, 2, 3, 4, 5]
        team_fdr = defaultdict(lambda: {gw: "-" for gw in next_gws})
        for fix in fixtures:
            gw = fix.get("event")
            if gw in next_gws:
                team_fdr[fix["team_h"]][gw] = fix.get("team_h_difficulty", 3)
                team_fdr[fix["team_a"]][gw] = fix.get("team_a_difficulty", 3)
        results = []
        for team_id, gw_diffs in team_fdr.items():
            values = [v for v in gw_diffs.values() if isinstance(v, (int, float))]
            avg = sum(values) / len(values) if values else 3.0
            row = {"Team": teams.get(team_id, "?")}
            for gw in next_gws:
                row[f"GW{gw}"] = gw_diffs[gw]
            row["Avg"] = round(avg, 2)
            results.append(row)
        results = sorted(results, key=lambda x: x["Avg"])
        st.dataframe(results, use_container_width=True, hide_index=True)
    else:
        st.error("Could not load fixture data.")

elif page == "Players - Easiest Fixtures":
    st.subheader("Players with Easiest Fixtures")
    st.caption("Sorted by easiest upcoming fixtures")
    if bootstrap and fixtures:
        teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
        positions = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        next_gws = []
        for event in bootstrap.get("events", []):
            if event.get("is_next") or (next_gws and len(next_gws) < 5):
                next_gws.append(event["id"])
                if len(next_gws) >= 5:
                    break
        if not next_gws:
            next_gws = [1, 2, 3, 4, 5]
        team_fdr = defaultdict(list)
        for fix in fixtures:
            gw = fix.get("event")
            if gw in next_gws:
                team_fdr[fix["team_h"]].append(fix.get("team_h_difficulty", 3))
                team_fdr[fix["team_a"]].append(fix.get("team_a_difficulty", 3))
        team_avg = {tid: sum(d)/len(d) for tid, d in team_fdr.items() if d}
        pos_choice = st.selectbox("Filter by position", ["All", "Goalkeepers", "Defenders", "Midfielders", "Forwards"])
        pos_map = {"Goalkeepers": 1, "Defenders": 2, "Midfielders": 3, "Forwards": 4}
        selected_pos = pos_map.get(pos_choice)
        players = []
        for p in bootstrap.get("elements", []):
            if selected_pos and p["element_type"] != selected_pos:
                continue
            avg = team_avg.get(p["team"], 3.0)
            players.append({
                "Pos": positions.get(p["element_type"], "?"),
                "Player": p["web_name"],
                "Team": teams.get(p["team"], "?"),
                "Price": round(p["now_cost"] / 10, 1),
                "Form": p.get("form", "-"),
                "Selected %": p.get("selected_by_percent", "-"),
                "Points": p.get("total_points", 0),
                "Avg FDR": round(avg, 2)
            })
        players = sorted(players, key=lambda x: x["Avg FDR"])[:30]
        st.dataframe(players, use_container_width=True, hide_index=True)
    else:
        st.error("Could not load data.")

elif page == "Transfer Suggestions":
    st.subheader("Transfer Suggestions")
    st.caption("Uses the entered Team ID when possible. Not financial advice.")
    if not bootstrap or not fixtures:
        st.error("Could not load data.")
    else:
        teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
        positions = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        owned_ids = set()
        squad_data = load_squad(TEAM_ID)
        if squad_data and "picks" in squad_data:
            owned_ids = {pick["element"] for pick in squad_data["picks"]}
            st.success(f"Loaded squad ({len(owned_ids)} players). Suggestions exclude owned players.")
        else:
            st.info("Could not load squad yet (normal in pre-season). Showing general suggestions.")
        next_gws = []
        for event in bootstrap.get("events", []):
            if event.get("is_next") or (next_gws and len(next_gws) < 5):
                next_gws.append(event["id"])
                if len(next_gws) >= 5:
                    break
        if not next_gws:
            next_gws = [1, 2, 3, 4, 5]
        team_fdr = defaultdict(list)
        for fix in fixtures:
            gw = fix.get("event")
            if gw in next_gws:
                team_fdr[fix["team_h"]].append(fix.get("team_h_difficulty", 3))
                team_fdr[fix["team_a"]].append(fix.get("team_a_difficulty", 3))
        team_avg = {tid: sum(d)/len(d) for tid, d in team_fdr.items() if d}
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            max_price = st.slider("Max price (£m)", 4.0, 15.0, 8.5, 0.5)
        with c2:
            max_fdr = st.slider("Max Avg FDR", 2.0, 4.0, 3.0, 0.1)
        with c3:
            min_owned = st.slider("Min ownership %", 0.0, 30.0, 2.0, 0.5)
        with c4:
            sort_by = st.selectbox("Sort by", ["Easiest fixtures", "Highest ownership", "Lowest price"])
        pos_choice = st.selectbox("Position", ["All", "Goalkeepers", "Defenders", "Midfielders", "Forwards"])
        pos_map = {"Goalkeepers": 1, "Defenders": 2, "Midfielders": 3, "Forwards": 4}
        selected_pos = pos_map.get(pos_choice)
        suggestions = []
        for p in bootstrap.get("elements", []):
            if p["id"] in owned_ids:
                continue
            if selected_pos and p["element_type"] != selected_pos:
                continue
            price = p["now_cost"] / 10
            avg = team_avg.get(p["team"], 3.0)
            owned = float(p.get("selected_by_percent", 0) or 0)
            if price <= max_price and avg <= max_fdr and owned >= min_owned:
                suggestions.append({
                    "Pos": positions.get(p["element_type"], "?"),
                    "Player": p["web_name"],
                    "Team": teams.get(p["team"], "?"),
                    "Price": round(price, 1),
                    "Avg FDR": round(avg, 2),
                    "Selected %": owned,
                    "Form": p.get("form", "-")
                })
        if sort_by == "Easiest fixtures":
            suggestions = sorted(suggestions, key=lambda x: (x["Avg FDR"], -x["Selected %"]))
        elif sort_by == "Highest ownership":
            suggestions = sorted(suggestions, key=lambda x: -x["Selected %"])
        else:
            suggestions = sorted(suggestions, key=lambda x: x["Price"])
        suggestions = suggestions[:25]
        if suggestions:
            st.dataframe(suggestions, use_container_width=True, hide_index=True)
        else:
            st.info("No players match your current filters.")
