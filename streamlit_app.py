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

def get_next_fixture_difficulty(team_id, fixtures, bootstrap):
    if not fixtures or not bootstrap:
        return 3
    next_gw = None
    for event in bootstrap.get("events", []):
        if event.get("is_next"):
            next_gw = event["id"]
            break
    if not next_gw:
        next_gw = 1
    for fix in fixtures:
        if fix.get("event") == next_gw:
            if fix.get("team_h") == team_id:
                return fix.get("team_h_difficulty", 3)
            if fix.get("team_a") == team_id:
                return fix.get("team_a_difficulty", 3)
    return 3

def potential_score(player, fixtures, bootstrap):
    try:
        form = float(player.get("form") or 0)
    except:
        form = 0
    try:
        ppg = float(player.get("points_per_game") or 0)
    except:
        ppg = 0
    fdr = get_next_fixture_difficulty(player.get("team"), fixtures, bootstrap)
    score = (form * 2.0) + (ppg * 1.5) + ((6 - fdr) * 3.0)
    return round(score, 2), fdr

def make_row(pid, players_by_id, teams, pos_map, fixtures, bootstrap):
    p = players_by_id.get(pid, {})
    change = p.get("cost_change_event", 0)
    change_str = ""
    if change > 0:
        change_str = f" ↑{change/10:.1f}"
    elif change < 0:
        change_str = f" ↓{abs(change)/10:.1f}"
    score, fdr = potential_score(p, fixtures, bootstrap)
    return {
        "id": pid,
        "Pos": pos_map.get(p.get("element_type"), "?"),
        "Player": p.get("web_name", "Unknown"),
        "Team": teams.get(p.get("team"), "?"),
        "Price": round(p.get("now_cost", 0) / 10, 1),
        "Change": change_str,
        "Form": p.get("form", "0.0"),
        "Points": p.get("total_points", 0),
        "PPG": p.get("points_per_game", "0.0"),
        "Next FDR": fdr,
        "Potential": score
    }

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
        "Manager",
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
elif page == "Manager":
    st.subheader("Manager")
    
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

    st.markdown("---")
    st.markdown("### History")
    st.caption("Points per gameweek, chips used, and past seasons")
    
    history = load_history(TEAM_ID)
    if not history:
        st.warning("Could not load history. This is normal in early pre-season.")
    else:
        current = history.get("current", [])
        chips = history.get("chips", [])
        past = history.get("past", [])

        if current:
            st.markdown("#### Current Season")
            rows = []
            for gw in current:
                rows.append({
                    "GW": gw.get("event"),
                    "Points": gw.get("points"),
                    "Total": gw.get("total_points"),
                    "Rank": gw.get("overall_rank"),
                    "GW Rank": gw.get("rank"),
                    "Transfers": gw.get("event_transfers"),
                    "Cost": gw.get("event_transfers_cost"),
                    "Value": round(gw.get("value", 0) / 10, 1) if gw.get("value") else "-"
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No gameweek history yet (season not started).")

        if chips:
            st.markdown("#### Chips Used")
            for chip in chips:
                st.write(f"- **{chip.get('name', 'Chip')}** in GW {chip.get('event')}")
        else:
            st.caption("No chips used yet.")

        if past:
            st.markdown("#### Previous Seasons")
            past_rows = [{"Season": s.get("season_name"), "Points": s.get("total_points"), "Rank": s.get("rank")} for s in past]
            st.dataframe(past_rows, use_container_width=True, hide_index=True)

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
    st.caption("Build squad → manage XI → auto captain → see best options inside your squad")

    if not bootstrap:
        st.error("Could not load player data.")
    else:
        players_by_id = {p["id"]: p for p in bootstrap["elements"]}
        teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
        pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        limits = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}

        # Session state
        if "saved_squad" not in st.session_state:
            st.session_state.saved_squad = []
        if "starting_xi" not in st.session_state:
            st.session_state.starting_xi = []
        if "captain" not in st.session_state:
            st.session_state.captain = None
        if "vice" not in st.session_state:
            st.session_state.vice = None
        if "working_squad" not in st.session_state:
            st.session_state.working_squad = list(st.session_state.saved_squad)
        if "sub_player" not in st.session_state:
            st.session_state.sub_player = None

        # ---------- SAVE / LOAD ----------
        st.markdown("### Save / Load Squad")
        st.caption("Your squad stays while you use the app. Use Download/Upload as a backup.")

        col_save, col_load = st.columns(2)

        with col_save:
            if len(st.session_state.saved_squad) == 15:
                import json
                squad_data = {
                    "saved_squad": st.session_state.saved_squad,
                    "starting_xi": st.session_state.starting_xi,
                    "captain": st.session_state.captain,
                    "vice": st.session_state.vice
                }
                json_str = json.dumps(squad_data, indent=2)
                st.download_button(
                    label="⬇️ Download Squad (Backup)",
                    data=json_str,
                    file_name="my_fpl_squad.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.info("Build and save a full 15-player squad first.")

        with col_load:
            uploaded_file = st.file_uploader(
                "⬆️ Upload previous squad",
                type=["json"],
                label_visibility="collapsed"
            )
            if uploaded_file is not None:
                try:
                    import json
                    data = json.load(uploaded_file)
                    st.session_state.saved_squad = data.get("saved_squad", [])
                    st.session_state.working_squad = list(st.session_state.saved_squad)
                    st.session_state.starting_xi = data.get("starting_xi", [])
                    st.session_state.captain = data.get("captain")
                    st.session_state.vice = data.get("vice")
                    st.success("Squad loaded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not load file: {e}")

        # ---------- BUILD SQUAD ----------
        st.markdown("### 1. Build your 15-man squad")

        pos_choice = st.selectbox("Select position to add from", ["GKP", "DEF", "MID", "FWD"])

        already_selected = set(st.session_state.working_squad)

        options = []
        option_ids = {}
        for p in bootstrap["elements"]:
            if pos_map[p["element_type"]] == pos_choice:
                label = f"{p['web_name']} ({teams.get(p['team'], '?')}) - £{p['now_cost']/10:.1f}m"
                options.append(label)
                option_ids[label] = p["id"]

        default_labels = [label for label, pid in option_ids.items() if pid in already_selected]

        selected = st.multiselect(
            f"Choose {pos_choice} players",
            options=options,
            default=default_labels,
            max_selections=limits[pos_choice],
            key=f"multi_{pos_choice}"
        )

        # Update working squad for this position
        new_working = []
        for pid in st.session_state.working_squad:
            p = players_by_id.get(pid)
            if p and pos_map[p["element_type"]] != pos_choice:
                new_working.append(pid)

        for label in selected:
            new_working.append(option_ids[label])

        st.session_state.working_squad = list(set(new_working))

        # Live counts
        counts = {"GKP": 0, "DEF": 0, "MID": 0, "FWD": 0}
        team_counts = {}
        for pid in st.session_state.working_squad:
            p = players_by_id.get(pid)
            if p:
                pos = pos_map[p["element_type"]]
                counts[pos] += 1
                team_id = p.get("team")
                team_counts[team_id] = team_counts.get(team_id, 0) + 1

        st.write(f"**Current counts:** GKP {counts['GKP']}/2 · DEF {counts['DEF']}/5 · MID {counts['MID']}/5 · FWD {counts['FWD']}/3  → **Total {len(st.session_state.working_squad)}/15**")

        full_teams = [teams.get(tid, "?") for tid, c in team_counts.items() if c >= 3]
        if full_teams:
            st.caption(f"Teams at max (3 players): {', '.join(full_teams)}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Squad", type="primary"):
                if len(st.session_state.working_squad) != 15:
                    st.error("You need exactly 15 players.")
                elif counts["GKP"] != 2 or counts["DEF"] != 5 or counts["MID"] != 5 or counts["FWD"] != 3:
                    st.error("Position counts must be exactly 2 GKP / 5 DEF / 5 MID / 3 FWD.")
                elif any(c > 3 for c in team_counts.values()):
                    st.error("Maximum 3 players from the same club.")
                else:
                    st.session_state.saved_squad = list(st.session_state.working_squad)
                    st.session_state.starting_xi = [pid for pid in st.session_state.starting_xi if pid in st.session_state.saved_squad]
                    if st.session_state.captain not in st.session_state.saved_squad:
                        st.session_state.captain = None
                    if st.session_state.vice not in st.session_state.saved_squad:
                        st.session_state.vice = None
                    st.success("Squad saved successfully!")
                    st.rerun()
        with col2:
            if st.button("Clear Squad"):
                st.session_state.saved_squad = []
                st.session_state.working_squad = []
                st.session_state.starting_xi = []
                st.session_state.captain = None
                st.session_state.vice = None
                st.session_state.sub_player = None
                st.rerun()

        # ---------- PITCH + MANAGEMENT (only when 15 players saved) ----------
        if len(st.session_state.saved_squad) == 15:

            # Ensure starting_xi is valid
            if not st.session_state.starting_xi:
                gk = [pid for pid in st.session_state.saved_squad if pos_map[players_by_id[pid]["element_type"]] == "GKP"]
                outfield = [pid for pid in st.session_state.saved_squad if pos_map[players_by_id[pid]["element_type"]] != "GKP"]
                st.session_state.starting_xi = (gk[:1] + outfield[:10]) if gk else outfield[:11]

            st.session_state.starting_xi = [pid for pid in st.session_state.starting_xi if pid in st.session_state.saved_squad]

            starters = [make_row(pid, players_by_id, teams, pos_map, fixtures, bootstrap) for pid in st.session_state.starting_xi]
            bench_ids = [pid for pid in st.session_state.saved_squad if pid not in st.session_state.starting_xi]
            bench = [make_row(pid, players_by_id, teams, pos_map, fixtures, bootstrap) for pid in bench_ids]

            valid, formation_msg = is_valid_formation(starters)

            if valid and len(starters) == 11:
                st.success(f"Valid formation: **{formation_msg}**")
            else:
                st.error(f"Invalid Starting XI: {formation_msg if len(starters) == 11 else 'Must have exactly 11 players'}")

            # Value & Bank
            total_value = sum(players_by_id[pid]["now_cost"] / 10 for pid in st.session_state.saved_squad if pid in players_by_id)
            bank = 100.0 - total_value
            c1, c2, c3 = st.columns(3)
            c1.metric("Squad Value", f"£{total_value:.1f}m")
            c2.metric("In the Bank", f"£{bank:.1f}m")
            c3.metric("Players", "15/15")

            # ---------- VISUAL PITCH ----------
            st.markdown("### Pitch View")

            gk = [r for r in starters if r["Pos"] == "GKP"]
            defs = [r for r in starters if r["Pos"] == "DEF"]
            mids = [r for r in starters if r["Pos"] == "MID"]
            fwds = [r for r in starters if r["Pos"] == "FWD"]

            def player_card(p, show_sub_button=False):
                is_c = st.session_state.captain == p["id"]
                is_v = st.session_state.vice == p["id"]
                badge = " ©️" if is_c else (" ⓥ" if is_v else "")
                card = f"**{p['Player']}{badge}**  \n{p['Team']} · £{p['Price']}m  \nFDR {p['Next FDR']}"

                if is_c:
                    st.success(card)
                elif is_v:
                    st.warning(card)
                else:
                    st.info(card)

                if show_sub_button and bench:
                    if st.button("⇄ Sub", key=f"sub_{p['id']}", use_container_width=True):
                        st.session_state.sub_player = p["id"]

            # GK
            if gk:
                c1, c2, c3 = st.columns([1.2, 1, 1.2])
                with c2:
                    player_card(gk[0], show_sub_button=True)

            # DEF
            if defs:
                cols = st.columns(len(defs))
                for i, p in enumerate(defs):
                    with cols[i]:
                        player_card(p, show_sub_button=True)

            # MID
            if mids:
                cols = st.columns(len(mids))
                for i, p in enumerate(mids):
                    with cols[i]:
                        player_card(p, show_sub_button=True)

            # FWD
            if fwds:
                cols = st.columns(len(fwds))
                for i, p in enumerate(fwds):
                    with cols[i]:
                        player_card(p, show_sub_button=True)

            st.caption("©️ = Captain   ·   ⓥ = Vice-Captain")

            # ---------- SUBSTITUTE UI ----------
            if st.session_state.sub_player:
                outgoing = next((r for r in starters if r["id"] == st.session_state.sub_player), None)
                if outgoing:
                    st.markdown("---")
                    st.markdown(f"**Substitute:** {outgoing['Player']} ({outgoing['Pos']})")
                    bench_options = {f"{b['Player']} ({b['Pos']}) - £{b['Price']}m": b["id"] for b in bench}
                    chosen = st.selectbox("Choose bench player to bring on", ["— Select player —"] + list(bench_options.keys()))

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Confirm Swap", type="primary") and chosen != "— Select player —":
                            incoming_id = bench_options[chosen]
                            st.session_state.starting_xi.remove(st.session_state.sub_player)
                            st.session_state.starting_xi.append(incoming_id)
                            if st.session_state.captain == st.session_state.sub_player:
                                st.session_state.captain = None
                            if st.session_state.vice == st.session_state.sub_player:
                                st.session_state.vice = None
                            st.session_state.sub_player = None
                            st.success("Swap completed!")
                            st.rerun()
                    with col2:
                        if st.button("Cancel"):
                            st.session_state.sub_player = None
                            st.rerun()

            # ---------- BENCH VISUAL ----------
            st.markdown("#### Bench")
            if bench:
                cols = st.columns(len(bench))
                for i, p in enumerate(bench):
                    with cols[i]:
                        player_card(p, show_sub_button=False)
            else:
                st.caption("No players on the bench")

            # Auto captain button
            if st.button("🤖 Auto-select Captain (best potential for next GW)"):
                if starters:
                    best = max(starters, key=lambda x: x["Potential"])
                    st.session_state.captain = best["id"]
                    others = [s for s in starters if s["id"] != best["id"]]
                    if others:
                        second = max(others, key=lambda x: x["Potential"])
                        st.session_state.vice = second["id"]
                    st.success(f"Captain set to **{best['Player']}**")
                    st.rerun()

            # ---------- DETAILED LISTS ----------
            st.markdown("**Starting XI**")
            for row in sorted(starters, key=lambda x: -x["Potential"]):
                cols = st.columns([1, 3, 1, 1.5, 1, 1, 1, 1, 1])
                cols[0].write(row["Pos"])
                cols[1].write(row["Player"])
                cols[2].write(row["Team"])
                cols[3].write(f"£{row['Price']}m{row['Change']}")
                cols[4].write(row["Form"])
                cols[5].write(row["Points"])
                cols[6].write(row["Next FDR"])
                cols[7].write(row["Potential"])
                with cols[8]:
                    c1, c2, c3 = st.columns(3)
                    is_c = st.session_state.captain == row["id"]
                    is_v = st.session_state.vice == row["id"]
                    if c1.button("C" if not is_c else "★", key=f"cap_{row['id']}"):
                        st.session_state.captain = row["id"]
                        if st.session_state.vice == row["id"]:
                            st.session_state.vice = None
                        st.rerun()
                    if c2.button("V" if not is_v else "★", key=f"vice_{row['id']}"):
                        st.session_state.vice = row["id"]
                        if st.session_state.captain == row["id"]:
                            st.session_state.captain = None
                        st.rerun()
                    if c3.button("↓", key=f"to_bench_{row['id']}"):
                        st.session_state.starting_xi.remove(row["id"])
                        if st.session_state.captain == row["id"]:
                            st.session_state.captain = None
                        if st.session_state.vice == row["id"]:
                            st.session_state.vice = None
                        st.rerun()

            cap_name = players_by_id.get(st.session_state.captain, {}).get("web_name", "None") if st.session_state.captain else "None"
            vice_name = players_by_id.get(st.session_state.vice, {}).get("web_name", "None") if st.session_state.vice else "None"
            st.caption(f"Captain: **{cap_name}**  |  Vice-Captain: **{vice_name}**")

            st.markdown("**Bench**")
            for row in bench:
                cols = st.columns([1, 3, 1, 1.5, 1, 1, 1, 1, 1])
                cols[0].write(row["Pos"])
                cols[1].write(row["Player"])
                cols[2].write(row["Team"])
                cols[3].write(f"£{row['Price']}m{row['Change']}")
                cols[4].write(row["Form"])
                cols[5].write(row["Points"])
                cols[6].write(row["Next FDR"])
                cols[7].write(row["Potential"])
                if len(st.session_state.starting_xi) < 11:
                    if cols[8].button("↑ XI", key=f"to_xi_{row['id']}"):
                        st.session_state.starting_xi.append(row["id"])
                        st.rerun()
                else:
                    cols[8].write("")

            st.markdown("---")
            st.markdown("### Best players in your squad for next GW")
            all_rows = starters + bench
            ranked = sorted(all_rows, key=lambda x: -x["Potential"])
            display = []
            for r in ranked:
                status = "C" if r["id"] == st.session_state.captain else ("V" if r["id"] == st.session_state.vice else ("XI" if r["id"] in st.session_state.starting_xi else "Bench"))
                display.append({
                    "Status": status,
                    "Pos": r["Pos"],
                    "Player": r["Player"],
                    "Team": r["Team"],
                    "Form": r["Form"],
                    "PPG": r["PPG"],
                    "Next FDR": r["Next FDR"],
                    "Potential": r["Potential"],
                    "Price": r["Price"]
                })
            st.dataframe(display, use_container_width=True, hide_index=True)

        elif len(st.session_state.saved_squad) > 0:
            st.warning(f"You currently have {len(st.session_state.saved_squad)}/15 players saved. Finish the squad first.")
        else:
            st.info("No players saved yet. Add players by position above, then click **Save Squad**.")
