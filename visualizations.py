# import sqlite3
# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns

# conn = sqlite3.connect("nba.db")
# cursor = conn.cursor()

# cursor.execute("SELECT * FROM play_by_play")
# all_plays = cursor.fetchall()
# df_all = pd.DataFrame(all_plays, columns=["game_id", "action_number", "period", "clock_seconds", "team_tricode", "action_type", "sub_type", "score_home", "score_away", "description", "shot_value", "is_field_goal"])

# cursor.execute("SELECT * FROM play_by_play WHERE action_type = 'Timeout'")
# timeouts = cursor.fetchall()
# df_timeouts = pd.DataFrame(timeouts, columns=["game_id", "action_number", "period", "clock_seconds", "team_tricode", "action_type", "sub_type", "score_home", "score_away", "description", "shot_value", "is_field_goal"])

# action_counts = df_all["action_type"].value_counts()

# # df_all["action_type"].value_counts().plot(kind="bar")
# # plt.show()

# # sns.histplot(data=df_timeouts, x="clock_seconds", hue="period", bins=12)
# # plt.xlabel("Seconds Remaining in Period")
# # plt.title("Timeout Timing by Period")
# # plt.gca().invert_xaxis()
# # plt.show()

# df_timeouts = df_timeouts[df_timeouts["period"] <= 4]

# sns.histplot(data=df_timeouts, x="clock_seconds", hue="period", bins=12)
# plt.gca().invert_xaxis()
# plt.xlabel("Seconds Remaining in Period")
# plt.title("Timeout Timing by Period")
# plt.show()

import sqlite3
conn = sqlite3.connect("nba.db")
cursor = conn.cursor()
cursor.execute("""
    SELECT game_id, game_date FROM games
    WHERE game_id BETWEEN '0021900600' AND '0021900610'
""")
print(cursor.fetchall())