import sqlite3
import time
import pandas as pd
from nba_api.stats.endpoints import playbyplayv3

custom_headers = {
    'Host': 'stats.nba.com',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
}

conn = sqlite3.connect("nba.db")
cursor = conn.cursor()

cursor.execute("SELECT game_id FROM games")
game_ids = cursor.fetchall()

# Get already collected game IDs
cursor.execute("SELECT DISTINCT game_id FROM play_by_play")
collected = set(row[0] for row in cursor.fetchall())
print(f"Already collected: {len(collected)} games, {len(game_ids) - len(collected)} remaining")

for i, (game_id,) in enumerate(game_ids):
    if game_id in collected:
        continue
    try:
        df = playbyplayv3.PlayByPlayV3(game_id=game_id, headers=custom_headers).get_data_frames()[0]
    except Exception as e:
        print(f"Failed on game {game_id}: {e}")
        with open("failed_games.txt", "a") as f:
            f.write(f"{game_id}\n")
        time.sleep(5)
        continue

    df = df[["gameId", "actionNumber", "period", "clock", "teamTricode", "actionType", "subType", "scoreHome", "scoreAway", "description", "shotValue", "isFieldGoal"]]

    # Convert clock to seconds
    split_clock = df["clock"].str.replace("PT", "").str.split("M")
    minutes = split_clock.str[0].astype(float)
    seconds = split_clock.str[1].str.replace("S", "").astype(float)
    df["clock_seconds"] = minutes * 60 + seconds
    df = df.drop(columns=["clock"])

    # Clean up score columns — empty strings become NULL
    df["scoreHome"] = pd.to_numeric(df["scoreHome"], errors="coerce")
    df["scoreAway"] = pd.to_numeric(df["scoreAway"], errors="coerce")

    rows = list(df.itertuples(index=False, name=None))

    cursor.executemany("""
        INSERT OR IGNORE INTO play_by_play 
        (game_id, action_number, period, team_tricode, action_type, sub_type, score_home, score_away, description, shot_value, is_field_goal, clock_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    if i % 100 == 0:
        print(f"Processing game {i}/{len(game_ids)}...")
        conn.commit()
        time.sleep(60)

    time.sleep(1.0)

conn.commit()
conn.close()
print("Done!")