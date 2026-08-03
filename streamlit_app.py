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

# ---------- DATA ----------
@st.cache_data(ttl=300)
def load_bootstrap():
    return get_data("https://fantasy.premierleague.com/api/bootstrap-static/")

@st.cache_data(ttl=300)
def load_entry(team_id):
    return get_data(f"https://fantasy.premierleague.com/api/entry/{team_id}/")

@st.cache_data(ttl=300)
def load_fixtures():
    return get_data("https://fantasy.premierleague.com/api/fixtures/")

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

# ---------- HELPERS ----------
def is_valid_formation(starters):
    counts = {"GKP": 0, "DEF": 0, "MID": 0, "FWD": 0}
    for p in starters:
        counts[p["Pos"]] += 1
    if counts["GKP"] != 1:
        return False, "Must have exactly 1 Goalkeeper"
    if counts["DEF"] < 3 or counts["DEF"] > 5:
        return False, "Must have 3–5 Defenders"
    if counts["MID"] < 2 or counts["MID"] > 5:
        return False, "Must have 2–5 Midfielders"
    if counts["FWD"] < 1 or counts["FWD"] > 3:
        return False, "Must have 1–3 Forwards"
    if counts["DEF"] + counts["MID"] + counts["FWD"] != 10:
        return False, "Outfield players must total 10"
    return True, f"{counts['DEF']}-{counts['MID']}-{counts['FWD']}"

def make_row(pid, players_by_id, teams, pos_map):
    p = players_by_id.get(pid, {})
    change = p.get("cost_change_event", 0)
    change_str = ""
    if change > 0:
        change_str = f" ↑{change/10:.1f}"
    elif change < 0:
        change_str = f" ↓{abs(change)/10:.1f}"
    return {
        "id": pid,
        "Pos": pos_map.get(p.get("element_type"), "?"),
        "Player": p.get("web_name", "Unknown"),
        "Team": teams.get(p.get("team"), "?"),
        "Price": round(p.get("now_cost", 0) / 10, 1),
        "Change": change_str,
        "raw_change": change
    }

def get_team_avg_fdr(fixtures, bootstrap, next_gws=5):
    if not fixtures or not bootstrap:
        return {}
    team_fdr = defaultdict(list)
    gws = []
    for event in bootstrap.get("events", []):
        if event.get("is_next") or (gws and len(gws) < next_gws):
            gws.append(event["id"])
            if len(gws) >= next_gws:
                break
    if not gws:
        gws = [1, 2, 3, 4, 5]
    for fix in fixtures:
        gw = fix.get("event")
        if gw in gws:
            team_fdr[fix["team_h"]].append(fix.get("team_h_difficulty", 3))
            team_fdr[fix["team_a"]].append(fix.get("team_a_difficulty", 3))
    return {tid: sum(d)/len(d) for tid, d in team_fdr.items() if d}

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
    st.caption("Build squad → set Starting XI → choose Captain/Vice → get swap ideas")

    if not bootstrap:
        st.error("Could not load player data.")
    else:
        players_by_id = {p["id"]: p for p in bootstrap["elements"]}
        teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
        pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        limits = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
        team_avg_fdr = get_team_avg_fdr(fixtures, bootstrap)

        if "saved_squad" not in st.session_state:
            st.session_state.saved_squad = []
        if "starting_xi" not in st.session_state:
            st.session_state.starting_xi = []
        if "captain" not in st.session_state:
            st.session_state.captain = None
        if "vice" not in st.session_state:
            st.session_state.vice = None

        # ---------- 1. BUILD 15-MAN SQUAD ----------
        st.markdown("### 1. Build your 15-man squad")
        pos_choice = st.selectbox("Select position to add from", ["GKP", "DEF", "MID", "FWD"])

        options = []
        option_ids = {}
        for p in bootstrap["elements"]:
            if pos_map[p["element_type"]] == pos_choice:
                label = f"{p['web_name']} ({teams.get(p['team'], '?')}) - £{p['now_cost']/10:.1f}m"
                options.append(label)
                option_ids[label] = p["id"]

        selected = st.multiselect(
            f"Choose {pos_choice} players",
            options=options,
            default=[label for label, pid in option_ids.items() if pid in st.session_state.saved_squad],
            max_selections=limits[pos_choice]
        )

        current_ids = set()
        for pid in st.session_state.saved_squad:
            p = players_by_id.get(pid)
            if p and pos_map[p["element_type"]] != pos_choice:
                current_ids.add(pid)
        for label in selected:
            current_ids.add(option_ids[label])

        working_squad = list(current_ids)

        counts = {"GKP": 0, "DEF": 0, "MID": 0, "FWD": 0}
        for pid in working_squad:
            p = players_by_id.get(pid)
            if p:
                counts[pos_map[p["element_type"]]] += 1

        st.write(f"**Current counts:** GKP {counts['GKP']}/2 · DEF {counts['DEF']}/5 · MID {counts['MID']}/5 · FWD {counts['FWD']}/3  → Total {len(working_squad)}/15")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Squad", type="primary"):
                final = []
                temp_counts = {"GKP": 0, "DEF": 0, "MID": 0, "FWD": 0}
                for pid in working_squad:
                    p = players_by_id.get(pid)
                    if not p:
                        continue
                    pos = pos_map[p["element_type"]]
                    if temp_counts[pos] < limits[pos]:
                        final.append(pid)
                        temp_counts[pos] += 1
                st.session_state.saved_squad = final
                st.session_state.starting_xi = [pid for pid in st.session_state.starting_xi if pid in final]
                if st.session_state.captain not in final:
                    st.session_state.captain = None
                if st.session_state.vice not in final:
                    st.session_state.vice = None
                st.success("Squad saved!")
                st.rerun()
        with col2:
            if st.button("Clear Squad"):
                st.session_state.saved_squad = []
                st.session_state.starting_xi = []
                st.session_state.captain = None
                st.session_state.vice = None
                st.rerun()

        # ---------- 2. MANAGE STARTING XI / BENCH / C / VC ----------
        if len(st.session_state.saved_squad) == 15:
            st.markdown("---")
            st.markdown("### 2. Starting XI, Bench, Captain & Swaps")

            total_value = sum(players_by_id[pid]["now_cost"] / 10 for pid in st.session_state.saved_squad if pid in players_by_id)
            bank = 100.0 - total_value

            c1, c2, c3 = st.columns(3)
            c1.metric("Squad Value", f"£{total_value:.1f}m")
            c2.metric("In the Bank", f"£{bank:.1f}m")
            c3.metric("Players", "15/15")

            # Auto default XI if empty
            if not st.session_state.starting_xi:
                gk = [pid for pid in st.session_state.saved_squad if pos_map[players_by_id[pid]["element_type"]] == "GKP"]
                outfield = [pid for pid in st.session_state.saved_squad if pos_map[players_by_id[pid]["element_type"]] != "GKP"]
                st.session_state.starting_xi = (gk[:1] + outfield[:10]) if gk else outfield[:11]

            st.session_state.starting_xi = [pid for pid in st.session_state.starting_xi if pid in st.session_state.saved_squad]

            starters = [make_row(pid, players_by_id, teams, pos_map) for pid in st.session_state.starting_xi]
            bench_ids = [pid for pid in st.session_state.saved_squad if pid not in st.session_state.starting_xi]
            bench = [make_row(pid, players_by_id, teams, pos_map) for pid in bench_ids]

            valid, formation_msg = is_valid_formation(starters)

            if valid and len(starters) == 11:
                st.success(f"Valid formation: **{formation_msg}**")
            else:
                st.error(f"Invalid Starting XI: {formation_msg if len(starters)==11 else 'Must have exactly 11 players'}")

            # ---- STARTING XI ----
            st.markdown("**Starting XI**")
            for row in starters:
                cols = st.columns([1, 3, 1, 2, 2, 1, 1, 2])
                cols[0].write(row["Pos"])
                cols[1].write(row["Player"])
                cols[2].write(row["Team"])
                cols[3].write(f"£{row['Price']}m{row['Change']}")
                
                # Captain / Vice
                is_c = st.session_state.captain == row["id"]
                is_v = st.session_state.vice == row["id"]
                if cols[4].button("C" if not is_c else "★ C", key=f"cap_{row['id']}"):
                    st.session_state.captain = row["id"]
                    if st.session_state.vice == row["id"]:
                        st.session_state.vice = None
                    st.rerun()
                if cols[5].button("V" if not is_v else "★ V", key=f"vice_{row['id']}"):
                    st.session_state.vice = row["id"]
                    if st.session_state.captain == row["id"]:
                        st.session_state.captain = None
                    st.rerun()

                if cols[6].button("↓", key=f"to_bench_{row['id']}", help="Move to bench"):
                    st.session_state.starting_xi.remove(row["id"])
                    if st.session_state.captain == row["id"]:
                        st.session_state.captain = None
                    if st.session_state.vice == row["id"]:
                        st.session_state.vice = None
                    st.rerun()

            # Show current C / VC
            cap_name = players_by_id.get(st.session_state.captain, {}).get("web_name", "None") if st.session_state.captain else "None"
            vice_name = players_by_id.get(st.session_state.vice, {}).get("web_name", "None") if st.session_state.vice else "None"
            st.caption(f"Captain: **{cap_name}**  |  Vice-Captain: **{vice_name}**")

            st.markdown("")
            # ---- BENCH ----
            st.markdown("**Bench**")
            for row in bench:
                cols = st.columns([1, 3, 1, 2, 2, 2])
                cols[0].write(row["Pos"])
                cols[1].write(row["Player"])
                cols[2].write(row["Team"])
                cols[3].write(f"£{row['Price']}m{row['Change']}")
                if len(st.session_state.starting_xi) < 11:
                    if cols[4].button("↑ XI", key=f"to_xi_{row['id']}"):
                        st.session_state.starting_xi.append(row["id"])
                        st.rerun()
                else:
                    cols[4].write("")

            # ---------- 3. NEXT BEST SWAP SUGGESTIONS ----------
            st.markdown("---")
            st.markdown("### 3. Next Best Swap Suggestions")
            st.caption("Select a player from your squad to see better alternatives in the same position (based on easier fixtures + similar price)")

            all_squad_rows = starters + bench
            swap_options = {f"{r['Pos']} | {r['Player']} (£{r['Price']}m)": r["id"] for r in all_squad_rows}
            chosen_label = st.selectbox("Player to improve", ["— Select a player —"] + list(swap_options.keys()))

            if chosen_label != "— Select a player —":
                chosen_id = swap_options[chosen_label]
                chosen = players_by_id[chosen_id]
                chosen_pos = chosen["element_type"]
                chosen_price = chosen["now_cost"] / 10
                chosen_fdr = team_avg_fdr.get(chosen["team"], 3.0)

                # Find alternatives: same position, price within ±1.5m, better (lower) FDR
                alternatives = []
                for p in bootstrap["elements"]:
                    if p["id"] == chosen_id:
                        continue
                    if p["element_type"] != chosen_pos:
                        continue
                    price = p["now_cost"] / 10
                    if abs(price - chosen_price) > 1.5:
                        continue
                    fdr = team_avg_fdr.get(p["team"], 3.0)
                    if fdr < chosen_fdr - 0.1:  # meaningfully easier
                        alternatives.append({
                            "Player": p["web_name"],
                            "Team": teams.get(p["team"], "?"),
                            "Price": round(price, 1),
                            "Avg FDR": round(fdr, 2),
                            "Selected %": p.get("selected_by_percent", "-"),
                            "Form": p.get("form", "-"),
                            "Diff": round(chosen_fdr - fdr, 2)
                        })

                alternatives = sorted(alternatives, key=lambda x: (x["Avg FDR"], x["Price"]))[:8]

                if alternatives:
                    st.success(f"Better fixture options than **{chosen['web_name']}** (current FDR {chosen_fdr:.2f})")
                    st.dataframe(alternatives, use_container_width=True, hide_index=True)
                else:
                    st.info("No clearly better alternatives found within ±£1.5m right now.")

        elif st.session_state.saved_squad:
            st.warning(f"You currently have {len(st.session_state.saved_squad)}/15 players. Finish the squad first.")
        else:
            st.info("No players saved yet. Add players by position above, then click **Save Squad**.")

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
    st.caption("Uses your saved squad when available. Not financial advice.")
    if not bootstrap or not fixtures:
        st.error("Could not load data.")
    else:
        teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
        positions = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        owned_ids = set(st.session_state.get("saved_squad", []))
        if owned_ids:
            st.success(f"Using your saved squad ({len(owned_ids)} players). Suggestions exclude them.")
        else:
            st.info("No saved squad yet. Build one on the Squad page for better suggestions.")

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
