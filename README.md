# Fitbit analysis

[Open the interactive Fitbit dashboard](https://fitbit-insight.streamlit.app/)

1. `pip install -r requirements.txt`
2. Put raw CSVs in `data_raw/` (already there), then `python build_db.py`
   -> creates `fitbit.db` and clean CSVs in `exports/`
3. `streamlit run app.py` (dashboard, SQL analysis, cleaning pages)
4. `python charts.py` -> Matplotlib/seaborn PNGs in `charts/`

## Power BI / Tableau
Connect to `exports/daily_master.csv` (one row per user per day). Add `hourly.csv`,
`heartrate_hourly.csv`, `sleep_day.csv`, `weight_log.csv` and relate on `user_id` (+ date).
Suggested pages: KPIs (steps, calories, sedentary hrs) / weekday + hour patterns / sleep vs activity / user segments.

## Cleaning decisions
- 72 non-wear days removed (0 steps and 1440 sedentary minutes)
- 3 duplicate sleep rows removed
- Weight: body fat almost empty (2 rows), so ignored; only 8 users logged weight
- Heart rate: only 14 users; aggregated from 2.4M second-level rows to hourly
- Timestamps converted from US `m/d/Y h:mm AM/PM` to ISO
