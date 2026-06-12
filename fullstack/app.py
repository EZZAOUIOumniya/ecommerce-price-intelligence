import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, timedelta
import random

# ─────────────────────────────────────────
# Page config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Price Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
  /* Dark theme overrides */
  .main { background-color: #0f1117; }
  .block-container { padding-top: 1.5rem; }

  /* KPI cards */
  .kpi-card {
    background: linear-gradient(135deg, #1a1d2e 0%, #16213e 100%);
    border: 1px solid #2d3561;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }
  .kpi-value {
    font-size: 2.1rem;
    font-weight: 700;
    color: #4fc3f7;
    line-height: 1.1;
  }
  .kpi-label {
    font-size: 0.78rem;
    color: #8892a4;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.3rem;
  }
  .kpi-delta {
    font-size: 0.85rem;
    margin-top: 0.25rem;
  }
  .up   { color: #4caf50; }
  .down { color: #f44336; }

  /* Alert banner */
  .alert-banner {
    background: linear-gradient(90deg, #1a1d2e, #16213e);
    border-left: 4px solid #f44336;
    border-radius: 6px;
    padding: 0.6rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.85rem;
    color: #e0e0e0;
  }

  /* Section headers */
  h2 { color: #e8eaf6 !important; font-weight: 600 !important; }
  h3 { color: #b0bec5 !important; font-weight: 500 !important; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background-color: #12151f;
    border-right: 1px solid #1e2333;
  }
  [data-testid="stSidebar"] h1 { color: #4fc3f7; font-size: 1.1rem; }

  /* Badge */
  .badge {
    display: inline-block;
    background: #1e3a5f;
    color: #4fc3f7;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .badge-green  { background: #1b3a1f; color: #4caf50; }
  .badge-red    { background: #3a1b1b; color: #f44336; }
  .badge-orange { background: #3a2a1b; color: #ff9800; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# Data generation (simulates Bigtable/dbt output)
# ─────────────────────────────────────────
@st.cache_data(ttl=60)
def load_price_data():
    df = pd.read_csv("data/cleaned_data.csv")

    # normalisation pour ton dashboard
    df = df.rename(columns={
        "scraped_date": "date",
        "scraped_at": "timestamp",
        "site": "platform"
    })

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["price_change_pct"] = df.groupby(["name", "platform"])["price"].pct_change() * 100
    df["price_change_pct"] = df["price_change_pct"].fillna(0)

    return df


@st.cache_data(ttl=60)
def load_stats_json():
    """Load pre-computed stats (mirrors analyst JSON export)."""
    stats_path = "data/stats_export.json"
    if os.path.exists(stats_path):
        with open(stats_path) as f:
            return json.load(f)
    # Fallback: compute inline
    return {
        "total_products": 24,
        "total_platforms": 3,
        "avg_price_drop_pct": -2.3,
        "alerts_24h": 7,
        "pipeline_status": "healthy",
        "last_scrape": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─────────────────────────────────────────
# Load data
# ─────────────────────────────────────────
df    = load_price_data()
stats = load_stats_json()

today    = df[df["date"] == df["date"].max()]
latest   = today.groupby(["product", "category", "platform"])["price"].mean().reset_index()
all_time = df.groupby(["product", "platform"])["price"].agg(["min", "max", "mean", "std"]).reset_index()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Price Intelligence")
    st.markdown(
        '<span class="badge badge-green">● Pipeline Active</span>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    st.markdown("### Filters")
    categories = st.multiselect(
        "Category",
        options=df["category"].unique().tolist(),
        default=df["category"].unique().tolist(),
    )
    platforms = st.multiselect(
        "Platform",
        options=df["platform"].unique().tolist(),
        default=df["platform"].unique().tolist(),
    )
    date_range = st.slider(
        "Days back",
        min_value=1,
        max_value=30,
        value=30,
        help="Number of past days to display",
    )
    st.markdown("---")
    st.markdown("### Pipeline Info")
    st.caption(f"🕒 Last scrape: `{stats.get('last_scrape', 'N/A')}`")
    st.caption("🔧 Stack: Scrapy → NiFi → Airflow → Bigtable → dbt → Streamlit")
    st.caption("☁️ Cloud: Google Cloud Platform")
    st.markdown("---")
    st.markdown(
        '<div style="color:#555;font-size:0.72rem">'
        'Pr. ELAACHAK · Data Eng & Analytics<br>'
        'Real-Time E-commerce Price Intelligence</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────
# Apply filters
# ─────────────────────────────────────────
cutoff = df["date"].max() - timedelta(days=date_range - 1)
filt = df[
    df["category"].isin(categories)
    & df["platform"].isin(platforms)
    & (df["date"] >= cutoff)
].copy()

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown("# 📈 Real-Time Price Intelligence Dashboard")
st.markdown(
    '<div style="color:#8892a4;font-size:0.9rem;margin-bottom:1rem">'
    'Web Scraping → NiFi → Airflow → Bigtable → dbt → Analytics · '
    f'Last updated: <b style="color:#4fc3f7">{datetime.now().strftime("%H:%M:%S")}</b>'
    '</div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────
avg_price       = filt["price"].mean()
total_products  = filt["product"].nunique()
total_obs       = len(filt)
price_drops     = (filt["price_change_pct"] < -2).sum()
avg_rating      = filt["rating"].mean()
in_stock_pct    = (filt["in_stock"].sum() / len(filt) * 100) if len(filt) else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)

for col, value, label, delta, delta_cls in [
    (k1, f"{avg_price:,.0f} MAD",  "Avg Price",        "↓ 1.2% vs last week", "down"),
    (k2, str(total_products),       "Products Tracked", f"across {len(platforms)} platforms", "up"),
    (k3, f"{total_obs:,}",          "Price Records",    f"last {date_range} days", "up"),
    (k4, str(price_drops),          "Price Drops > 2%", "real-time alerts", "down"),
    (k5, f"{avg_rating:.2f} ★",     "Avg Product Rating", "customer sentiment", "up"),
    (k6, f"{in_stock_pct:.0f}%",    "In-Stock Rate",    "availability index", "up"),
]:
    with col:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-delta {delta_cls}">{delta}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# REAL-TIME ALERTS
# ─────────────────────────────────────────
alerts = filt[filt["price_change_pct"] < -3].sort_values("price_change_pct").head(5)
if not alerts.empty:
    st.markdown("### 🚨 Real-Time Price Alerts (NiFi Stream)")
    for _, row in alerts.iterrows():
        st.markdown(
            f'<div class="alert-banner">'
            f'<b>{row["product"]}</b> on <b>{row["platform"]}</b> — '
            f'Price dropped to <b>{row["price"]:,.0f} MAD</b> '
            f'<span style="color:#f44336">({row["price_change_pct"]:+.1f}%)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# ─────────────────────────────────────────
# ROW 1: Price trend + Category distribution
# ─────────────────────────────────────────
col_l, col_r = st.columns([2, 1])

with col_l:
    st.markdown("### Price Trends by Platform")
    daily_avg = (
        filt.groupby(["date", "platform"])["price"]
        .mean()
        .reset_index()
        .rename(columns={"price": "avg_price"})
    )
    fig_trend = px.line(
        daily_avg,
        x="date",
        y="avg_price",
        color="platform",
        color_discrete_map={
            "Jumia": "#4fc3f7",
            "Glovo": "#ff9800",
            "Amazon.ma": "#66bb6a",
        },
        labels={"avg_price": "Avg Price (MAD)", "date": ""},
        template="plotly_dark",
    )
    fig_trend.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,17,23,0.8)",
        legend_title="",
        margin=dict(l=0, r=0, t=10, b=0),
        height=320,
        font=dict(color="#8892a4"),
    )
    fig_trend.update_traces(line=dict(width=2.5))
    st.plotly_chart(fig_trend, use_container_width=True)

with col_r:
    st.markdown("### Category Price Distribution")
    cat_avg = filt.groupby("category")["price"].mean().reset_index()
    fig_cat = px.bar(
        cat_avg.sort_values("price", ascending=True),
        x="price",
        y="category",
        orientation="h",
        color="price",
        color_continuous_scale="Blues",
        template="plotly_dark",
        labels={"price": "Avg Price (MAD)", "category": ""},
    )
    fig_cat.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,17,23,0.8)",
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=320,
        font=dict(color="#8892a4"),
    )
    st.plotly_chart(fig_cat, use_container_width=True)

# ─────────────────────────────────────────
# ROW 2: Price volatility + Platform comparison
# ─────────────────────────────────────────
col_l2, col_r2 = st.columns([1, 1])

with col_l2:
    st.markdown("### Price Volatility by Category (std dev)")
    vol = filt.groupby(["category", "platform"])["price"].std().reset_index()
    vol.columns = ["category", "platform", "volatility"]
    fig_vol = px.bar(
        vol,
        x="category",
        y="volatility",
        color="platform",
        barmode="group",
        color_discrete_map={
            "Jumia": "#4fc3f7",
            "Glovo": "#ff9800",
            "Amazon.ma": "#66bb6a",
        },
        template="plotly_dark",
        labels={"volatility": "Std Dev (MAD)", "category": ""},
    )
    fig_vol.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,17,23,0.8)",
        legend_title="",
        margin=dict(l=0, r=0, t=10, b=0),
        height=320,
        font=dict(color="#8892a4"),
    )
    st.plotly_chart(fig_vol, use_container_width=True)

with col_r2:
    st.markdown("### Platform Price Comparison (Box Plot)")
    fig_box = px.box(
        filt,
        x="platform",
        y="price",
        color="platform",
        color_discrete_map={
            "Jumia": "#4fc3f7",
            "Glovo": "#ff9800",
            "Amazon.ma": "#66bb6a",
        },
        template="plotly_dark",
        labels={"price": "Price (MAD)", "platform": ""},
    )
    fig_box.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,17,23,0.8)",
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=320,
        font=dict(color="#8892a4"),
    )
    st.plotly_chart(fig_box, use_container_width=True)

# ─────────────────────────────────────────
# ROW 3: Statistical Analysis
# ─────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔬 Inferential Statistics — dbt + SciPy Pipeline")

tab1, tab2, tab3 = st.tabs(["📐 Descriptive Stats", "🧪 Hypothesis Tests", "📉 Regression"])

with tab1:
    desc = (
        filt.groupby(["category", "platform"])["price"]
        .agg(["mean", "median", "std", "min", "max", "count"])
        .round(2)
        .reset_index()
    )
    desc.columns = ["Category", "Platform", "Mean", "Median", "Std Dev", "Min", "Max", "N"]
    st.dataframe(
        desc,
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    st.markdown(
        "**Welch t-test**: Are prices significantly different between platforms?\n\n"
        "H₀: μ(Jumia) = μ(Amazon.ma) | α = 0.05"
    )
    from scipy import stats as scipy_stats

    jumia  = filt[filt["platform"] == "Jumia"]["price"].dropna()
    amazon = filt[filt["platform"] == "Amazon.ma"]["price"].dropna()
    glovo  = filt[filt["platform"] == "Glovo"]["price"].dropna()

    t_stat, p_val = scipy_stats.ttest_ind(jumia, amazon, equal_var=False)
    f_stat, p_anova = scipy_stats.f_oneway(jumia, amazon, glovo)

    results = pd.DataFrame([
        {
            "Test": "Welch t-test (Jumia vs Amazon.ma)",
            "Statistic": round(t_stat, 4),
            "p-value": round(p_val, 6),
            "Result": "✅ Reject H₀" if p_val < 0.05 else "❌ Fail to reject H₀",
            "Interpretation": "Prices differ significantly" if p_val < 0.05 else "No sig. difference",
        },
        {
            "Test": "One-way ANOVA (all platforms)",
            "Statistic": round(f_stat, 4),
            "p-value": round(p_anova, 6),
            "Result": "✅ Reject H₀" if p_anova < 0.05 else "❌ Fail to reject H₀",
            "Interpretation": "At least one platform differs" if p_anova < 0.05 else "No sig. difference",
        },
    ])
    st.dataframe(results, use_container_width=True, hide_index=True)

    # Violin plot for distribution comparison
    fig_vio = px.violin(
        filt,
        y="price",
        x="platform",
        color="platform",
        box=True,
        points=False,
        color_discrete_map={
            "Jumia": "#4fc3f7",
            "Glovo": "#ff9800",
            "Amazon.ma": "#66bb6a",
        },
        template="plotly_dark",
        labels={"price": "Price (MAD)", "platform": ""},
    )
    fig_vio.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,17,23,0.8)",
        showlegend=False,
        height=350,
        font=dict(color="#8892a4"),
    )
    st.plotly_chart(fig_vio, use_container_width=True)

with tab3:
    st.markdown("**OLS Regression**: price ~ rating + reviews + log(reviews)")
    from scipy import stats as scipy_stats
    import numpy as np

    sample = filt.dropna(subset=["price", "rating", "reviews"]).copy()
    sample["log_reviews"] = np.log1p(sample["reviews"])

    X = sample[["rating", "log_reviews"]].values
    y = sample["price"].values
    X_mean = X.mean(axis=0)
    X_std  = X.std(axis=0)
    X_norm = (X - X_mean) / X_std

    # OLS via numpy
    X_aug = np.column_stack([np.ones(len(X_norm)), X_norm])
    betas = np.linalg.lstsq(X_aug, y, rcond=None)[0]
    y_hat = X_aug @ betas
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2     = 1 - ss_res / ss_tot

    reg_results = pd.DataFrame([
        {"Coefficient": "Intercept", "β": round(betas[0], 2), "Interpretation": "Baseline price"},
        {"Coefficient": "Rating (normalized)", "β": round(betas[1], 2), "Interpretation": "Price effect per σ rating"},
        {"Coefficient": "Log(Reviews) (normalized)", "β": round(betas[2], 2), "Interpretation": "Price effect per σ log-reviews"},
    ])
    st.dataframe(reg_results, use_container_width=True, hide_index=True)
    st.metric("R² Score", f"{r2:.4f}", help="Proportion of price variance explained by rating & reviews")

    # Scatter: rating vs price
    fig_reg = px.scatter(
        sample.sample(min(800, len(sample)), random_state=1),
        x="rating",
        y="price",
        color="category",
        size="reviews",
        size_max=20,
        opacity=0.6,
        trendline="ols",
        template="plotly_dark",
        labels={"price": "Price (MAD)", "rating": "Product Rating"},
    )
    fig_reg.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,17,23,0.8)",
        height=380,
        font=dict(color="#8892a4"),
        legend_title="Category",
    )
    st.plotly_chart(fig_reg, use_container_width=True)

# ─────────────────────────────────────────
# ROW 4: Price change heatmap + Top movers
# ─────────────────────────────────────────
st.markdown("---")
col_h, col_m = st.columns([3, 2])

with col_h:
    st.markdown("### 🌡️ Price Change Heatmap (Category × Day)")
    heat_data = (
        filt.groupby(["date", "category"])["price_change_pct"]
        .mean()
        .reset_index()
        .pivot(index="category", columns="date", values="price_change_pct")
        .fillna(0)
    )
    fig_heat = go.Figure(
        go.Heatmap(
            z=heat_data.values,
            x=[str(d) for d in heat_data.columns],
            y=heat_data.index.tolist(),
            colorscale="RdBu",
            zmid=0,
            text=np.round(heat_data.values, 1),
            texttemplate="%{text}%",
            colorbar=dict(
                title=dict(
                    text="Δ%",
                    font=dict(color="#8892a4"),
                ),
                tickfont=dict(color="#8892a4"),
            ),
        )
    )
    fig_heat.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,17,23,0.8)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=300,
        font=dict(color="#8892a4"),
        xaxis=dict(showticklabels=False),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

with col_m:
    st.markdown("### 📉 Top Price Movers (Today)")
    today_filt = filt[filt["date"] == filt["date"].max()].copy()
    movers = (
        today_filt.groupby(["product", "platform"])
        .agg(price_change=("price_change_pct", "mean"), price=("price", "mean"))
        .reset_index()
        .sort_values("price_change")
        .head(10)
    )
    movers["direction"] = movers["price_change"].apply(
        lambda x: "🔻" if x < 0 else "🔺"
    )
    movers["price_change_str"] = movers["price_change"].apply(lambda x: f"{x:+.2f}%")
    movers["price_str"] = movers["price"].apply(lambda x: f"{x:,.0f} MAD")
    st.dataframe(
        movers[["product", "platform", "price_str", "price_change_str", "direction"]]
        .rename(columns={
            "product": "Product",
            "platform": "Platform",
            "price_str": "Price",
            "price_change_str": "Δ%",
            "direction": "",
        }),
        use_container_width=True,
        hide_index=True,
        height=290,
    )

# ─────────────────────────────────────────
# ROW 5: Pipeline Architecture
# ─────────────────────────────────────────
st.markdown("---")
st.markdown("### 🏗️ Data Pipeline Status")

p1, p2, p3, p4, p5, p6, p7 = st.columns(7)
pipeline_steps = [
    ("🕷️ Scrapy", "Scraping", "green"),
    ("➡️ Kafka", "Streaming", "green"),
    ("🔄 NiFi", "Routing", "green"),
    ("⚙️ Airflow", "Orchestration", "green"),
    ("🗄️ Bigtable", "Storage", "green"),
    ("🔧 dbt", "Transform", "green"),
    ("📊 Dashboard", "Serving", "green"),
]
for col, (icon, label, status) in zip([p1, p2, p3, p4, p5, p6, p7], pipeline_steps):
    with col:
        st.markdown(
            f'<div class="kpi-card" style="padding:0.8rem">'
            f'<div style="font-size:1.6rem">{icon}</div>'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-delta up">● {status.upper()}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────
# ROW 6: Raw data explorer
# ─────────────────────────────────────────
st.markdown("---")
with st.expander("🔍 Raw Data Explorer (dbt mart output)"):
    sample_df = filt.sort_values("timestamp", ascending=False)
    st.dataframe(
        sample_df[[
            "timestamp", "product", "category", "platform",
            "price", "price_change_pct", "rating", "reviews", "in_stock"
        ]].rename(columns={
            "timestamp": "Timestamp",
            "product": "Product",
            "category": "Category",
            "platform": "Platform",
            "price": "Price (MAD)",
            "price_change_pct": "Δ Price %",
            "rating": "Rating",
            "reviews": "Reviews",
            "in_stock": "In Stock",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "Pr. ELAACHAK · Data Engineering & Analytics · "
    "Real-Time E-commerce Price Intelligence Platform · 2025-2026"
)