-- name: Data quality summary
SELECT 'daily rows (raw)' AS metric, COUNT(*) AS value FROM raw_daily_activity
UNION ALL SELECT 'daily rows (clean)', COUNT(*) FROM daily_activity
UNION ALL SELECT 'non-wear days removed', (SELECT COUNT(*) FROM raw_daily_activity) - (SELECT COUNT(*) FROM daily_activity)
UNION ALL SELECT 'sleep rows (raw)', COUNT(*) FROM raw_sleep_day
UNION ALL SELECT 'sleep rows (clean)', COUNT(*) FROM sleep_day
UNION ALL SELECT 'users with daily data', COUNT(DISTINCT user_id) FROM daily_activity
UNION ALL SELECT 'users with sleep data', COUNT(DISTINCT user_id) FROM sleep_day
UNION ALL SELECT 'users with heart-rate data', COUNT(DISTINCT user_id) FROM heartrate_hourly
UNION ALL SELECT 'users with weight data', COUNT(DISTINCT user_id) FROM weight_log;

-- name: Averages across all user-days
SELECT ROUND(AVG(total_steps)) AS avg_steps, ROUND(AVG(calories)) AS avg_calories,
       ROUND(AVG(sedentary_min)/60.0, 1) AS avg_sedentary_hours,
       ROUND(AVG(very_active_min + fairly_active_min), 1) AS avg_moderate_plus_min
FROM daily_activity;

-- name: Steps and calories by day of week
SELECT day_of_week, ROUND(AVG(total_steps)) AS avg_steps, ROUND(AVG(calories)) AS avg_calories,
       ROUND(AVG(sedentary_min)/60.0,1) AS avg_sedentary_hr
FROM daily_activity GROUP BY dow_num, day_of_week ORDER BY dow_num;

-- name: Steps and calories by hour of day
SELECT hour_of_day, ROUND(AVG(steps), 1) AS avg_steps, ROUND(AVG(calories), 1) AS avg_calories
FROM hourly GROUP BY hour_of_day ORDER BY hour_of_day;

-- name: User segments by activity level
SELECT activity_level, COUNT(*) AS user_days,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM daily_activity), 1) AS pct_of_days,
       ROUND(AVG(calories)) AS avg_calories
FROM daily_activity GROUP BY activity_level ORDER BY MIN(total_steps);

-- name: Steps vs calories by user (top 10 by steps)
SELECT user_id, COUNT(*) AS days_tracked, ROUND(AVG(total_steps)) AS avg_steps,
       ROUND(AVG(calories)) AS avg_calories, ROUND(AVG(sedentary_min)/60.0,1) AS avg_sedentary_hr
FROM daily_activity GROUP BY user_id ORDER BY avg_steps DESC LIMIT 10;

-- name: Sleep vs activity (daily join)
SELECT CASE WHEN minutes_asleep < 360 THEN '<6h' WHEN minutes_asleep < 420 THEN '6-7h'
            WHEN minutes_asleep < 480 THEN '7-8h' ELSE '8h+' END AS sleep_bucket,
       COUNT(*) AS nights, ROUND(AVG(total_steps)) AS avg_steps_same_day,
       ROUND(AVG(calories)) AS avg_calories, ROUND(AVG(sleep_efficiency_pct),1) AS avg_efficiency_pct
FROM daily_master WHERE minutes_asleep IS NOT NULL
GROUP BY sleep_bucket ORDER BY MIN(minutes_asleep);

-- name: Time in bed not asleep
SELECT ROUND(AVG(minutes_awake_in_bed),1) AS avg_min_awake_in_bed,
       ROUND(AVG(sleep_efficiency_pct),1) AS avg_efficiency_pct,
       ROUND(100.0*SUM(minutes_asleep < 420)/COUNT(*),1) AS pct_nights_under_7h
FROM sleep_day;

-- name: Heart rate by hour of day
SELECT hour_of_day, ROUND(AVG(avg_bpm),1) AS avg_bpm, MIN(min_bpm) AS min_bpm, MAX(max_bpm) AS max_bpm
FROM heartrate_hourly GROUP BY hour_of_day ORDER BY hour_of_day;

-- name: Device usage (days tracked per user)
SELECT CASE WHEN days >= 28 THEN 'Heavy (28+ days)' WHEN days >= 15 THEN 'Moderate (15-27)' ELSE 'Light (<15)' END AS usage_group,
       COUNT(*) AS users, ROUND(AVG(avg_steps)) AS avg_steps
FROM (SELECT user_id, COUNT(*) AS days, AVG(total_steps) AS avg_steps FROM daily_activity GROUP BY user_id)
GROUP BY usage_group;

-- name: Weight log coverage
SELECT user_id, COUNT(*) AS entries, ROUND(MIN(weight_kg),1) AS min_kg, ROUND(MAX(weight_kg),1) AS max_kg,
       ROUND(AVG(bmi),1) AS avg_bmi, SUM(is_manual) AS manual_entries
FROM weight_log GROUP BY user_id ORDER BY entries DESC;
