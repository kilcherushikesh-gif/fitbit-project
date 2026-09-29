-- Cleaning layer (SQLite). Raw tables are loaded by build_db.py with dates already ISO-formatted.

DROP TABLE IF EXISTS daily_activity;
CREATE TABLE daily_activity AS
SELECT DISTINCT
    Id                           AS user_id,
    ActivityDate                 AS activity_date,
    CAST(strftime('%w', ActivityDate) AS INTEGER) AS dow_num,
    CASE strftime('%w', ActivityDate)
        WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue' WHEN '3' THEN 'Wed'
        WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri' ELSE 'Sat' END AS day_of_week,
    TotalSteps                   AS total_steps,
    ROUND(TotalDistance, 2)      AS total_distance_km,
    VeryActiveMinutes            AS very_active_min,
    FairlyActiveMinutes          AS fairly_active_min,
    LightlyActiveMinutes         AS lightly_active_min,
    SedentaryMinutes             AS sedentary_min,
    Calories                     AS calories,
    VeryActiveMinutes + FairlyActiveMinutes + LightlyActiveMinutes AS active_min,
    CASE WHEN TotalSteps < 5000  THEN 'Sedentary (<5k)'
         WHEN TotalSteps < 7500  THEN 'Low active (5-7.5k)'
         WHEN TotalSteps < 10000 THEN 'Somewhat active (7.5-10k)'
         ELSE 'Active (10k+)' END AS activity_level
FROM raw_daily_activity
-- drop days where the tracker was not worn: zero steps and a full 1440 min of sedentary time
WHERE NOT (TotalSteps = 0 AND SedentaryMinutes = 1440);

DROP TABLE IF EXISTS sleep_day;
CREATE TABLE sleep_day AS
SELECT DISTINCT                      -- removes the exact duplicate rows in the export
    Id                AS user_id,
    SleepDay          AS sleep_date,
    TotalSleepRecords AS sleep_records,
    TotalMinutesAsleep AS minutes_asleep,
    TotalTimeInBed    AS minutes_in_bed,
    TotalTimeInBed - TotalMinutesAsleep AS minutes_awake_in_bed,
    ROUND(100.0 * TotalMinutesAsleep / TotalTimeInBed, 1) AS sleep_efficiency_pct
FROM raw_sleep_day;

DROP TABLE IF EXISTS weight_log;
CREATE TABLE weight_log AS
SELECT DISTINCT
    Id AS user_id,
    date(Date) AS weigh_date,
    ROUND(WeightKg, 1) AS weight_kg,
    Fat AS body_fat_pct,               -- mostly NULL: only 2 rows populated
    ROUND(BMI, 1) AS bmi,
    CASE WHEN IsManualReport IN ('True', 1, '1') THEN 1 ELSE 0 END AS is_manual
FROM raw_weight_log;

DROP TABLE IF EXISTS hourly;
CREATE TABLE hourly AS
SELECT s.Id AS user_id,
       s.ActivityHour AS activity_hour,
       date(s.ActivityHour) AS activity_date,
       CAST(strftime('%H', s.ActivityHour) AS INTEGER) AS hour_of_day,
       s.StepTotal AS steps,
       c.Calories AS calories,
       i.TotalIntensity AS total_intensity
FROM raw_hourly_steps s
JOIN raw_hourly_calories c    ON c.Id = s.Id AND c.ActivityHour = s.ActivityHour
JOIN raw_hourly_intensities i ON i.Id = s.Id AND i.ActivityHour = s.ActivityHour;

DROP TABLE IF EXISTS heartrate_hourly;
CREATE TABLE heartrate_hourly AS
SELECT Id AS user_id,
       date(Time) AS hr_date,
       CAST(strftime('%H', Time) AS INTEGER) AS hour_of_day,
       ROUND(AVG(Value), 1) AS avg_bpm,
       MIN(Value) AS min_bpm,
       MAX(Value) AS max_bpm,
       COUNT(*) AS readings
FROM raw_heartrate_seconds
GROUP BY Id, date(Time), CAST(strftime('%H', Time) AS INTEGER);

-- Sleep stage rollup from minute-level data (1 = asleep, 2 = restless, 3 = awake)
DROP TABLE IF EXISTS sleep_minutes_summary;
CREATE TABLE sleep_minutes_summary AS
SELECT Id AS user_id, date(date) AS sleep_date,
       SUM(value = 1) AS asleep_min,
       SUM(value = 2) AS restless_min,
       SUM(value = 3) AS awake_min
FROM raw_minute_sleep
GROUP BY Id, date(date);

-- One row per user per day, joining everything (the table Power BI / Tableau should use)
DROP TABLE IF EXISTS daily_master;
CREATE TABLE daily_master AS
SELECT a.*,
       s.minutes_asleep, s.minutes_in_bed, s.sleep_efficiency_pct,
       h.avg_bpm AS avg_resting_proxy_bpm
FROM daily_activity a
LEFT JOIN sleep_day s ON s.user_id = a.user_id AND s.sleep_date = a.activity_date
LEFT JOIN (SELECT user_id, hr_date, ROUND(AVG(avg_bpm),1) AS avg_bpm
           FROM heartrate_hourly GROUP BY user_id, hr_date) h
       ON h.user_id = a.user_id AND h.hr_date = a.activity_date;

CREATE INDEX IF NOT EXISTS ix_dm ON daily_master(user_id, activity_date);
