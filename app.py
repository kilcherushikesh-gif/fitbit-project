"""Fitbit activity dashboard. Run:  python build_db.py  then  streamlit run app.py"""
import re, sqlite3
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
DB = ROOT / "fitbit.db"
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
st.set_page_config(page_title="Fitbit Insights", page_icon="🏃", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #eef4ff 0%, #f8fafc 22%, #f5f7fb 100%);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #14213d 0%, #1f2f52 100%);
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stDateInput label,
    [data-testid="stSidebar"] .stRadio label {
        color: #e7ecff !important;
        font-weight: 600;
    }
    [data-testid="stSidebar"] .st-bb,
    [data-testid="stSidebar"] .st-bd,
    [data-testid="stSidebar"] .st-bc {
        background: rgba(255,255,255,0.06);
        color: white;
    }
    [data-testid="stSidebar"] .st-cq {
        color: white;
    }
    [data-testid="stMetric"] {
        background: rgba(255,255,255,.78);
        border: 1px solid rgba(23, 41, 70, 0.08);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 8px 24px rgba(20, 33, 61, 0.06);
    }
    [data-testid="stMetricLabel"] {
        color: #52677d !important;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: #14213d !important;
        font-weight: 700;
    }
    .section-header {
        margin-top: 1rem;
        margin-bottom: 0.55rem;
        font-size: 1.12rem;
        font-weight: 700;
        color: #243b5d;
        letter-spacing: 0.01em;
    }
    .stTabs [role="tablist"] {
        gap: 0.5rem;
    }
    .stTabs [role="tab"] {
        background: rgba(255,255,255,0.7);
        border-radius: 10px 10px 0 0;
        padding: 0.5rem 1rem;
    }
    @media (max-width: 640px) {
        .block-container {
            padding: 1.25rem 1rem 2rem;
        }
        [data-testid="stMetric"] {
            padding: 0.8rem;
            border-radius: 14px;
        }
        .stTabs [role="tablist"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_resource
def conn():
    return sqlite3.connect(DB, check_same_thread=False)

@st.cache_data
def sql(query: str) -> pd.DataFrame:
    return pd.read_sql(query, conn())

@st.cache_data
def named_queries() -> dict:
    txt = (ROOT / "sql" / "02_analysis.sql").read_text()
    return {n.strip(): q.strip() + ";" for n, q in re.findall(r"-- name: (.*?)\n(.*?);", txt, flags=re.S)}

if not DB.exists():
    st.error("fitbit.db not found. Run `python build_db.py` first."); st.stop()

st.sidebar.markdown(
    """
    <div style='padding: 1.2rem 0.6rem 0.6rem 0.6rem; text-align: center;'>
        <div style='font-size: 1.25rem; font-weight:800; color:#f6f8ff; letter-spacing: 0.02em;'>Fitbit Insights</div>
        <div style='font-size: 0.72rem; color: rgba(255,255,255,0.75); margin-top: 0.3rem;'>Health + activity dashboard</div>
    </div>
    """,
    unsafe_allow_html=True,
)
page = st.sidebar.radio("Page", ["Dashboard", "SQL analysis", "Data cleaning"])

# ---------- Dashboard ----------
if page == "Dashboard":
    st.title("Fitbit activity dashboard")
    st.caption("Daily movement, sleep, and recovery trends across the dataset")
    daily = sql("SELECT * FROM daily_master")
    users = st.sidebar.multiselect("Users (blank = all)", sorted(daily.user_id.unique()))
    lo, hi = daily.activity_date.min(), daily.activity_date.max()
    dates = st.sidebar.date_input("Date range", (pd.to_datetime(lo), pd.to_datetime(hi)))
    df = daily.copy()
    if users: df = df[df.user_id.isin(users)]
    if len(dates) == 2:
        df = df[(df.activity_date >= str(dates[0])) & (df.activity_date <= str(dates[1]))]
    if df.empty: st.warning("No data for this filter."); st.stop()

    with st.container(horizontal=True):
        st.metric("Users", df.user_id.nunique(), border=True)
        st.metric("Avg steps / day", f"{df.total_steps.mean():,.0f}", border=True)
        st.metric("Avg calories / day", f"{df.calories.mean():,.0f}", border=True)
        st.metric("Sedentary hrs / day", f"{df.sedentary_min.mean()/60:.1f}", border=True)
        st.metric("Avg sleep (h)", f"{df.minutes_asleep.mean()/60:.1f}" if df.minutes_asleep.notna().any() else "n/a", border=True)
    st.download_button(
        "Download filtered data",
        df.to_csv(index=False).encode("utf-8"),
        "fitbit-filtered-activity.csv",
        "text/csv",
        icon=":material/download:",
    )

    a, b = st.columns(2, wrap=True)
    with a:
        st.markdown("<div class='section-header'>Steps by weekday</div>", unsafe_allow_html=True)
        weekday = (
            df.assign(day_of_week=pd.Categorical(df.day_of_week, categories=DOW, ordered=True))
            .groupby("day_of_week", observed=False).total_steps.mean()
            .rename("avg_steps").reset_index()
        )
        bars = alt.Chart(weekday).mark_bar(color="#477B86", cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("day_of_week:N", title=None, sort=DOW),
            y=alt.Y("avg_steps:Q", title="Average steps", scale=alt.Scale(zero=True)),
            tooltip=[alt.Tooltip("day_of_week:N", title="Weekday"), alt.Tooltip("avg_steps:Q", title="Average steps", format=",.0f")],
        )
        target = alt.Chart(pd.DataFrame({"steps": [10000]})).mark_rule(color="#C75B39", strokeDash=[5, 4]).encode(
            y=alt.Y("steps:Q")
        )
        st.altair_chart((bars + target).interactive(), width="stretch")
    with b:
        st.markdown("<div class='section-header'>Steps vs calories</div>", unsafe_allow_html=True)
        scatter = alt.Chart(df).mark_circle(size=65, opacity=0.7).encode(
            x=alt.X("total_steps:Q", title="Steps per day"),
            y=alt.Y("calories:Q", title="Calories burned"),
            color=alt.Color("activity_level:N", title="Activity level"),
            tooltip=[
                alt.Tooltip("user_id:N", title="User"),
                alt.Tooltip("activity_date:T", title="Date"),
                alt.Tooltip("total_steps:Q", title="Steps", format=",.0f"),
                alt.Tooltip("calories:Q", title="Calories", format=",.0f"),
            ],
        ).interactive()
        st.altair_chart(scatter, width="stretch")

    a, b = st.columns(2, wrap=True)
    with a:
        st.markdown("<div class='section-header'>Hourly activity pattern</div>", unsafe_allow_html=True)
        h = sql("SELECT hour_of_day, ROUND(AVG(steps),1) AS steps FROM hourly GROUP BY hour_of_day")
        st.line_chart(h.set_index("hour_of_day"), color="#4C78A8")
    with b:
        st.markdown("<div class='section-header'>Sleep vs steps</div>", unsafe_allow_html=True)
        s = df.dropna(subset=["minutes_asleep"])
        if s.empty: st.info("No sleep data for this selection.")
        else:
            sleep_scatter = alt.Chart(s).mark_circle(size=65, opacity=0.65).encode(
                x=alt.X("minutes_asleep:Q", title="Minutes asleep"),
                y=alt.Y("total_steps:Q", title="Steps that day"),
                color=alt.Color("activity_level:N", title="Activity level"),
                tooltip=[
                    alt.Tooltip("user_id:N", title="User"),
                    alt.Tooltip("minutes_asleep:Q", title="Minutes asleep", format=",.0f"),
                    alt.Tooltip("total_steps:Q", title="Steps", format=",.0f"),
                ],
            )
            seven_hours = alt.Chart(pd.DataFrame({"minutes_asleep": [420]})).mark_rule(
                color="#C75B39", strokeDash=[5, 4]
            ).encode(x="minutes_asleep:Q")
            st.altair_chart((sleep_scatter + seven_hours).interactive(), width="stretch")

    st.markdown("<div class='section-header'>Heart rate by hour</div>", unsafe_allow_html=True)
    hr = sql("SELECT hour_of_day, ROUND(AVG(avg_bpm),1) AS avg_bpm FROM heartrate_hourly GROUP BY hour_of_day")
    st.line_chart(hr.set_index("hour_of_day"), color="#F58518")

# ---------- SQL analysis ----------
elif page == "SQL analysis":
    st.title("SQL analysis")
    qs = named_queries()
    choice = st.selectbox("Saved query", list(qs))
    query = st.text_area("SQL (editable)", qs[choice], height=220)
    if st.button("Run", type="primary"):
        try:
            res = sql(query)
            st.dataframe(res, width="stretch")
            num = res.select_dtypes("number").columns
            if len(res) > 1 and len(num) and len(res) <= 60:
                st.bar_chart(res.set_index(res.columns[0])[num[0]])
            st.download_button("Download CSV", res.to_csv(index=False), "result.csv")
        except Exception as e:
            st.error(e)
    with st.expander("Tables you can query"):
        st.dataframe(sql("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'raw_%'"))

# ---------- Cleaning ----------
else:
    st.title("Data cleaning (SQL)")
    st.markdown("Raw CSVs are loaded as `raw_*` tables, then `sql/01_cleaning.sql` builds the clean tables.")
    st.dataframe(sql(named_queries()["Data quality summary"]), width="stretch")
    st.code((ROOT / "sql" / "01_cleaning.sql").read_text(), language="sql")
