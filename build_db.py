"""Load raw Fitbit CSVs into SQLite, run the cleaning SQL, export clean tables for Power BI / Tableau."""
import sqlite3, pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent
RAW, DB, OUT = ROOT / "data_raw", ROOT / "fitbit.db", ROOT / "exports"
OUT.mkdir(exist_ok=True)

# file -> (table, datetime columns, date-only columns)
SOURCES = {
    "dailyActivity.csv":      ("raw_daily_activity", [], ["ActivityDate"]),
    "sleepDay.csv":           ("raw_sleep_day", [], ["SleepDay"]),
    "weightLog.csv":          ("raw_weight_log", ["Date"], []),
    "hourlySteps.csv":        ("raw_hourly_steps", ["ActivityHour"], []),
    "hourlyCalories.csv":     ("raw_hourly_calories", ["ActivityHour"], []),
    "hourlyIntensities.csv":  ("raw_hourly_intensities", ["ActivityHour"], []),
    "minuteSleep.csv":        ("raw_minute_sleep", ["date"], []),
    "heartrateSeconds.csv":   ("raw_heartrate_seconds", ["Time"], []),
}

def load():
    con = sqlite3.connect(DB)
    for f, (table, dt_cols, d_cols) in SOURCES.items():
        path = RAW / f
        if not path.exists():
            if f == "heartrateSeconds.csv":
                df = pd.DataFrame(columns=["Id", "Time", "Value"])
                df.to_sql(table, con, if_exists="replace", index=False)
                print(f"{table:28s} {0:>9,} rows (source file missing; created empty table)")
                continue
            raise FileNotFoundError(f"Missing required raw file: {path}")

        df = pd.read_csv(path)
        for c in dt_cols:   # US format "4/12/2016 7:21:00 AM" -> ISO so SQLite date functions work
            df[c] = pd.to_datetime(df[c], format="%m/%d/%Y %I:%M:%S %p").dt.strftime("%Y-%m-%d %H:%M:%S")
        for c in d_cols:
            df[c] = pd.to_datetime(df[c], format="%m/%d/%Y", errors="coerce").fillna(
                pd.to_datetime(df[c], format="%m/%d/%Y %I:%M:%S %p", errors="coerce")).dt.strftime("%Y-%m-%d")
        df.to_sql(table, con, if_exists="replace", index=False)
        print(f"{table:28s} {len(df):>9,} rows")
    con.executescript((ROOT / "sql" / "01_cleaning.sql").read_text())
    con.commit()
    for t in ["daily_activity", "daily_master", "sleep_day", "weight_log", "hourly", "heartrate_hourly", "sleep_minutes_summary"]:
        pd.read_sql(f"SELECT * FROM {t}", con).to_csv(OUT / f"{t}.csv", index=False)
    con.close()
    print("Built", DB, "and exported clean CSVs to", OUT)

if __name__ == "__main__":
    load()
