from collections import defaultdict

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
