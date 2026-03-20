import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from sklearn.metrics import RocCurveDisplay
from sklearn.linear_model import LogisticRegression
import matplotlib.pyplot as plt

"""
model.py

Trains a Random Forest classifier to predict whether a timeout called
during an 8-0+ scoring run will be effective in slowing the run team's
subsequent scoring (defined as <= 4 points in the next 5 possessions).

Input:  runs table from nba.db
Output: Classification report, feature importance chart, confusion matrix,
        ROC curve saved to images/, and Logistic Regression comparison
Author: Darshan Balaji
"""

conn = sqlite3.connect("nba.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM runs")
rows = cursor.fetchall()
columns = ["game_id", "run_team", "run_points", "start_action", "end_action", "timeout_called", "pts_allowed_after", "period", "clock_seconds", "score_margin","timeout_team_is_home"]
runs_df = pd.DataFrame(rows, columns=columns)
# Define timeout as effective if run team scores 4 or fewer points after
runs_df["timeout_effective"] = (runs_df["pts_allowed_after"] <= 4).astype(int)
conn.close()
# Only train on runs where a timeout was called
model_df = runs_df[runs_df["timeout_called"] == 1]

X = model_df[["run_points", "period", "clock_seconds", "score_margin", "timeout_team_is_home"]]
Y = model_df["timeout_effective"]

# 80/20 train/test split with fixed random state for reproducibility
X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

features = ["run_points", "period", "clock_seconds", "score_margin", "timeout_team_is_home"]
importances = model.feature_importances_

plt.barh(features, importances)
plt.xlabel("Feature Importance")
plt.title("What Predicts Timeout Effectiveness?")
plt.savefig("images/feature_importance.png", dpi=150, bbox_inches="tight")
plt.show()

scores = cross_val_score(model, X, Y, cv=5)
print(f"Cross validation scores: {scores}")
print(f"Mean accuracy: {scores.mean():.2f}")
print(f"Standard deviation: {scores.std():.2f}")

cm = confusion_matrix(y_test, y_pred)
ConfusionMatrixDisplay(cm, display_labels=["Ineffective", "Effective"]).plot()
plt.title("Timeout Effectiveness Predictions")
plt.savefig("images/confusion_matrix.png", dpi=150, bbox_inches="tight")
plt.show()

RocCurveDisplay.from_estimator(model, X_test, y_test)
plt.title("ROC Curve - Timeout Effectiveness Model")
plt.savefig("images/roc_curve.png", dpi=150, bbox_inches="tight")
plt.show()

log_model = LogisticRegression(class_weight="balanced", max_iter=1000)
log_model.fit(X_train, y_train)
y_pred_log = log_model.predict(X_test)
print("Logistic Regression:")
print(classification_report(y_test, y_pred_log))

log_scores = cross_val_score(log_model, X, Y, cv=5)
print(f"Logistic Regression CV scores: {log_scores}")
print(f"Mean accuracy: {log_scores.mean():.2f}")
print(f"Standard deviation: {log_scores.std():.2f}")
