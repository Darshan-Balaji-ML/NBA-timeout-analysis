import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

"""
journalism_viz.py

Generates a publication-style visualization of NBA timeout timing
by quarter across 600+ regular season games.

Input:  play_by_play table from nba.db
Output: timeout_timing.png saved to images/
Author: Darshan Balaji
"""
# --- Load Data ---
conn = sqlite3.connect("nba.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM play_by_play WHERE action_type = 'Timeout'")
rows = cursor.fetchall()
columns = ["game_id", "action_number", "period", "clock_seconds", "team_tricode",
           "action_type", "sub_type", "score_home", "score_away", "description",
           "shot_value", "is_field_goal"]
conn.close()

df_timeouts = pd.DataFrame(rows, columns=columns)

# --- Filter & Clean ---
df_timeouts = df_timeouts[df_timeouts["period"] <= 4].copy()
df_timeouts["quarter"] = df_timeouts["period"].map({1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"})

# --- Plot ---
fig, ax = plt.subplots(figsize=(12, 6))

palette = {"Q1": "#c6d9f0", "Q2": "#89b4d9", "Q3": "#4a86c1", "Q4": "#1a3a5c"}

sns.histplot(
    data=df_timeouts,
    x="clock_seconds",
    hue="quarter",
    hue_order=["Q1", "Q2", "Q3", "Q4"],
    bins=12,
    multiple="stack",
    palette=palette,
    ax=ax
)

# Flip x-axis so it reads like a game clock counting down
ax.invert_xaxis()

# Labels & titles
ax.set_xlabel("Seconds Remaining in Period", fontsize=12)
ax.set_ylabel("Number of Timeouts", fontsize=12)
ax.set_title("NBA Coaches Save Their Timeouts for the Final Two Minutes",
             fontsize=16, fontweight="bold", pad=15)
ax.text(0.5, 1.01, "Timeout frequency across 600 NBA regular season games (2019–20 season) by quarter",
        transform=ax.transAxes, fontsize=10, color="gray", ha="center")

# Annotation pointing to the end-of-game spike
ax.annotate(
    "Q4 timeouts spike\nin the final 60 seconds",
    xy=(30, 400),
    xytext=(100, 820),
    arrowprops=dict(arrowstyle="->", color="black"),
    fontsize=10,
    color="#1a3a5c",
    fontweight="bold",
    ha="center"
)

# Clean up legend
legend = ax.get_legend()
legend.set_title("Quarter")

# Light grid for readability
ax.yaxis.set_major_locator(ticker.MultipleLocator(100))
ax.grid(axis="y", linestyle="--", alpha=0.5)
ax.set_facecolor("#f9f9f9")
fig.patch.set_facecolor("#f9f9f9")

plt.tight_layout()
plt.savefig("timeout_timing.png", dpi=150, bbox_inches="tight")
plt.show()