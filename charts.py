"""Static Matplotlib/seaborn charts -> charts/*.png"""
import sqlite3, pandas as pd, seaborn as sns, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "charts"; OUT.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid", context="talk")
con = sqlite3.connect(ROOT / "fitbit.db")
q = lambda s: pd.read_sql(s, con)
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def save(name):
    plt.tight_layout(); plt.savefig(OUT / f"{name}.png", dpi=130); plt.close()

# 1 steps vs calories, coloured by activity level
d = q("SELECT * FROM daily_activity")
plt.figure(figsize=(10, 6))
sns.scatterplot(d, x="total_steps", y="calories", hue="activity_level", alpha=.7)
sns.regplot(d, x="total_steps", y="calories", scatter=False, color="black", line_kws={"lw": 1.5})
plt.title("Steps vs calories burned"); plt.xlabel("Total steps"); plt.ylabel("Calories")
save("01_steps_vs_calories")

# 2 avg steps by weekday
plt.figure(figsize=(9, 5))
sns.barplot(d, x="day_of_week", y="total_steps", order=DOW, color="#4C78A8", errorbar=None)
plt.axhline(10000, ls="--", color="grey"); plt.title("Average steps by weekday"); plt.xlabel(""); plt.ylabel("Steps")
save("02_steps_by_weekday")

# 3 hourly pattern
h = q("SELECT hour_of_day, AVG(steps) steps, AVG(calories) calories FROM hourly GROUP BY hour_of_day")
fig, ax = plt.subplots(figsize=(10, 5))
sns.lineplot(h, x="hour_of_day", y="steps", marker="o", ax=ax, color="#4C78A8")
ax.set_xlabel("Hour of day"); ax.set_ylabel("Avg steps per hour"); ax.set_xticks(range(0, 24, 2))
ax.set_title("When are users active?")
save("03_hourly_steps")

# 4 sleep vs steps + sleep efficiency
m = q("SELECT * FROM daily_master WHERE minutes_asleep IS NOT NULL")
plt.figure(figsize=(10, 6))
sns.scatterplot(m, x="minutes_asleep", y="total_steps", alpha=.6)
plt.axvline(420, ls="--", color="grey"); plt.title("Sleep duration vs steps (dashed = 7h)")
plt.xlabel("Minutes asleep"); plt.ylabel("Steps that day")
save("04_sleep_vs_steps")

# 5 sedentary minutes distribution
plt.figure(figsize=(9, 5))
sns.histplot(d.sedentary_min / 60, bins=25, kde=True, color="#E45756")
plt.title("Sedentary hours per day"); plt.xlabel("Hours")
save("05_sedentary_hours")

# 6 correlation heatmap
cols = ["total_steps", "calories", "very_active_min", "fairly_active_min", "lightly_active_min",
        "sedentary_min", "minutes_asleep", "sleep_efficiency_pct"]
plt.figure(figsize=(9, 7))
sns.heatmap(m[cols].corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0, cbar=False)
plt.title("Correlations"); plt.xticks(rotation=40, ha="right")
save("06_correlations")

# 7 heart rate by hour
hr = q("SELECT hour_of_day, avg_bpm FROM heartrate_hourly")
plt.figure(figsize=(10, 5))
sns.lineplot(hr, x="hour_of_day", y="avg_bpm", errorbar="sd", marker="o")
plt.title("Average heart rate by hour (14 users)"); plt.xlabel("Hour of day"); plt.ylabel("BPM")
save("07_heartrate_by_hour")
print(sorted(p.name for p in OUT.iterdir()))
