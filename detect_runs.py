import sqlite3
import pandas as pd

# --- Connect to DB ---
conn = sqlite3.connect("nba.db")
cursor = conn.cursor()

# --- Drop and Recreate Runs Table ---
cursor.execute("DROP TABLE IF EXISTS runs")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        game_id VARCHAR,
        run_team VARCHAR,
        run_points INT,
        start_action INT,
        end_action INT,
        timeout_called BOOL,
        pts_allowed_after FLOAT,
        period INT,
        clock_seconds FLOAT,
        score_margin INT,
        timeout_team_is_home BOOL,
        PRIMARY KEY (game_id, start_action)
    )
""")
conn.commit()

# --- Load Play by Play Data ---
cursor.execute("SELECT * FROM play_by_play ORDER BY game_id, action_number")
rows = cursor.fetchall()
columns = ["game_id", "action_number", "period", "clock_seconds", "team_tricode",
           "action_type", "sub_type", "score_home", "score_away", "description",
           "shot_value", "is_field_goal"]
df = pd.DataFrame(rows, columns=columns)

# --- Load Games Data ---
cursor.execute("SELECT game_id, home_team_tricode, visitor_team_tricode FROM games")
games_rows = cursor.fetchall()
games_df = pd.DataFrame(games_rows, columns=["game_id", "home_team_tricode", "visitor_team_tricode"])

# --- Filter to Scoring Events ---
scoring = df[df["action_type"].isin(["Made Shot", "Free Throw"]) & df["score_home"].notna()].copy()
scoring["home_pts"] = scoring.groupby("game_id")["score_home"].diff()
scoring["away_pts"] = scoring.groupby("game_id")["score_away"].diff()
scoring["scoring_team"] = scoring.apply(
    lambda row: row["team_tricode"] if row["home_pts"] > 0 or row["away_pts"] > 0 else None, axis=1
)


# --- Run Detection ---
def detect_runs(game_df):
    current_team = None
    current_pts = 0
    current_start = None
    runs = []
    run_active = False

    for i, row in game_df.iterrows():
        if row["scoring_team"] == current_team:
            current_pts += row["shot_value"]
        else:
            if run_active and current_pts >= 8:
                runs.append({
                    "game_id": row["game_id"],
                    "run_team": current_team,
                    "run_points": current_pts,
                    "start_action": current_start,
                    "end_action": row["action_number"]
                })

            current_team = row["scoring_team"]
            current_pts = row["shot_value"]
            current_start = row["action_number"]
            run_active = False

        if current_pts >= 8:
            run_active = True

    return runs


# --- Run Detection Loop ---
all_runs = []
for game_id in scoring["game_id"].unique():
    game_df = scoring[scoring["game_id"] == game_id].reset_index(drop=True)
    all_runs.extend(detect_runs(game_df))

print(f"Total runs detected: {len(all_runs)}")

# --- Identify Timeouts During Runs ---
timeouts = df[df["action_type"] == "Timeout"]

def check_timeout(run):
    mask = (
        (timeouts["game_id"] == run["game_id"]) &
        (timeouts["action_number"] >= run["start_action"]) &
        (timeouts["action_number"] <= run["end_action"]) &
        (timeouts["team_tricode"] != run["run_team"])
    )
    return timeouts[mask].shape[0] > 0


# --- Next 5 Possessions + Score Margin + Home/Away ---
def get_next_possessions(run, df, games_df, n=5):
    game_df = df[df["game_id"] == run["game_id"]]

    # --- Game Info ---
    game_info = games_df[games_df["game_id"] == run["game_id"]]
    if game_info.empty:
        return None

    home_tricode = game_info["home_team_tricode"].values[0]
    visitor_tricode = game_info["visitor_team_tricode"].values[0]

    # --- Score Margin at Start of Run ---
    start_event = game_df[game_df["action_number"] <= run["start_action"]].dropna(subset=["score_home", "score_away"]).tail(1)
    score_margin = None
    if not start_event.empty:
        score_home = start_event["score_home"].values[0]
        score_away = start_event["score_away"].values[0]
        if run["run_team"] == home_tricode:
            score_margin = score_home - score_away
        else:
            score_margin = score_away - score_home

    # --- Timeout Team Home/Away ---
    trailing_team = home_tricode if run["run_team"] != home_tricode else visitor_tricode
    timeout_team_is_home = bool(trailing_team == home_tricode)

    if run["timeout_called"] == 1:
        timeout_event = game_df[
            (game_df["action_type"] == "Timeout") &
            (game_df["action_number"] >= run["start_action"]) &
            (game_df["action_number"] <= run["end_action"]) &
            (game_df["team_tricode"] != run["run_team"])
        ]
        if timeout_event.empty:
            return None
        timeout_action = timeout_event["action_number"].values[0]
        timeout_period = timeout_event["period"].values[0]
        timeout_clock = timeout_event["clock_seconds"].values[0]
        after_point = game_df[game_df["action_number"] > timeout_action]
    else:
        after_point = game_df[game_df["action_number"] > run["end_action"]]
        first_event = after_point[
            after_point["action_type"].isin(["Made Shot", "Free Throw"]) &
            after_point["score_home"].notna()
        ].head(1)
        timeout_period = first_event["period"].values[0] if not first_event.empty else None
        timeout_clock = first_event["clock_seconds"].values[0] if not first_event.empty else None

    scoring = after_point[
        after_point["action_type"].isin(["Made Shot", "Free Throw"]) &
        after_point["score_home"].notna()
    ]
    next_n = scoring.head(n)
    run_team_pts = next_n[next_n["team_tricode"] == run["run_team"]]["shot_value"].sum()

    return {
        "pts_allowed_after": run_team_pts,
        "period": timeout_period,
        "clock_seconds": timeout_clock,
        "score_margin": score_margin,
        "timeout_team_is_home": timeout_team_is_home
    }


runs_df = pd.DataFrame(all_runs)
runs_df["timeout_called"] = runs_df.apply(check_timeout, axis=1)

results = runs_df.apply(lambda run: get_next_possessions(run, df, games_df), axis=1)
runs_df["pts_allowed_after"] = results.apply(lambda x: x["pts_allowed_after"] if x is not None else None)
runs_df["period"] = results.apply(lambda x: x["period"] if x is not None else None)
runs_df["clock_seconds"] = results.apply(lambda x: x["clock_seconds"] if x is not None else None)
runs_df["score_margin"] = results.apply(lambda x: x["score_margin"] if x is not None else None)
runs_df["timeout_team_is_home"] = results.apply(lambda x: x["timeout_team_is_home"] if x is not None else None)

print(runs_df["timeout_called"].value_counts())
print(runs_df.head(10))

# --- Insert Runs into DB ---
rows = list(runs_df.itertuples(index=False, name=None))
cursor.executemany("""
    INSERT OR IGNORE INTO runs (game_id, run_team, run_points, start_action, end_action, timeout_called, pts_allowed_after, period, clock_seconds, score_margin, timeout_team_is_home)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", rows)

conn.commit()
conn.close()
print("Runs saved to database!")