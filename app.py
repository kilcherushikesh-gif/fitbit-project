"""Fitbit activity dashboard. Run:  python build_db.py  then  streamlit run app.py"""
import re, sqlite3
from pathlib import Path
import pandas as pd, seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st

ROOT = Path(__file__).parent
DB = ROOT / "fitbit.db"
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
sns.set_theme(style="whitegrid", rc={
    "axes.facecolor": "#f7f9fc",
    "figure.facecolor": "#f7f9fc",
    "axes.edgecolor": "#dde6f1",
    "grid.color": "#e9eef5",
    "axes.labelcolor": "#30465c",
    "xtick.color": "#30465c",
    "ytick.color": "#30465c",
    "text.color": "#30465c",
})
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

    c = st.columns(5)
    c[0].metric("Users", df.user_id.nunique())
    c[1].metric("Avg steps / day", f"{df.total_steps.mean():,.0f}")
    c[2].metric("Avg calories / day", f"{df.calories.mean():,.0f}")
    c[3].metric("Sedentary hrs / day", f"{df.sedentary_min.mean()/60:.1f}")
    c[4].metric("Avg sleep (h)", f"{df.minutes_asleep.mean()/60:.1f}" if df.minutes_asleep.notna().any() else "n/a")

    a, b = st.columns(2)
    with a:
        st.markdown("<div class='section-header'>Steps by weekday</div>", unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(6, 3.6))
        sns.barplot(df, x="day_of_week", y="total_steps", order=DOW, errorbar=None, color="#4C78A8", ax=ax)
        ax.axhline(10000, ls="--", color="grey"); ax.set_xlabel(""); ax.set_ylabel("Steps")
        st.pyplot(fig)
    with b:
        st.markdown("<div class='section-header'>Steps vs calories</div>", unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(6, 3.6))
        sns.scatterplot(df, x="total_steps", y="calories", hue="activity_level", alpha=.7, ax=ax)
        ax.legend(fontsize=7)
        st.pyplot(fig)

    a, b = st.columns(2)
    with a:
        st.markdown("<div class='section-header'>Hourly activity pattern</div>", unsafe_allow_html=True)
        h = sql("SELECT hour_of_day, ROUND(AVG(steps),1) AS steps FROM hourly GROUP BY hour_of_day")
        st.line_chart(h.set_index("hour_of_day"), color="#4C78A8")
    with b:
        st.markdown("<div class='section-header'>Sleep vs steps</div>", unsafe_allow_html=True)
        s = df.dropna(subset=["minutes_asleep"])
        if s.empty: st.info("No sleep data for this selection.")
        else:
            fig, ax = plt.subplots(figsize=(6, 3.6))
            sns.scatterplot(s, x="minutes_asleep", y="total_steps", alpha=.6, ax=ax)
            ax.axvline(420, ls="--", color="grey")
            st.pyplot(fig)

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
            st.dataframe(res, use_container_width=True)
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
    st.dataframe(sql(named_queries()["Data quality summary"]), use_container_width=True)
    st.code((ROOT / "sql" / "01_cleaning.sql").read_text(), language="sql")
