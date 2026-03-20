import sqlite3
import time
from nba_api.stats.endpoints import leaguegamefinder

conn = sqlite3.connect("nba.db")
cursor = conn.cursor()

# --- Drop and Recreate Games Table ---
cursor.execute("DROP TABLE IF EXISTS games")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS games (
        game_id VARCHAR PRIMARY KEY,
        season VARCHAR,
        game_date VARCHAR,
        home_team_id VARCHAR,
        visitor_team_id VARCHAR,
        home_team_tricode VARCHAR,
        visitor_team_tricode VARCHAR
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS play_by_play (
        game_id VARCHAR,
        action_number INT,
        period INT,
        clock_seconds FLOAT,
        team_tricode VARCHAR,
        action_type VARCHAR,
        sub_type VARCHAR,
        score_home INT,
        score_away INT,
        description VARCHAR,
        shot_value INT,
        is_field_goal BOOL,
        PRIMARY KEY(game_id, action_number)
    )
""")

conn.commit()

seasons = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]

for season in seasons:
    print(f"Fetching {season}...")

    finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        league_id_nullable="00",
        season_type_nullable="Regular Season"
    )

    df = finder.get_data_frames()[0]

    for game_id in df["GAME_ID"].unique():
        home_row = df[(df["GAME_ID"] == game_id) & (df["MATCHUP"].str.contains("vs."))]
        away_row = df[(df["GAME_ID"] == game_id) & (df["MATCHUP"].str.contains("@"))]

        if home_row.empty or away_row.empty:
            continue

        home_tricode = home_row["TEAM_ABBREVIATION"].values[0]
        visitor_tricode = away_row["TEAM_ABBREVIATION"].values[0]
        home_team_id = int(home_row["TEAM_ID"].values[0])
        visitor_team_id = int(away_row["TEAM_ID"].values[0])

        cursor.execute("""
            INSERT OR IGNORE INTO games (game_id, season, game_date, home_team_id, visitor_team_id, home_team_tricode, visitor_team_tricode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (game_id, season, home_row["GAME_DATE"].values[0], home_team_id, visitor_team_id, home_tricode, visitor_tricode))

    conn.commit()
    time.sleep(0.7)

cursor.execute("SELECT COUNT(*) FROM games")
print(cursor.fetchone())

cursor.execute("SELECT * FROM games LIMIT 5")
print(cursor.fetchall())

conn.close()

