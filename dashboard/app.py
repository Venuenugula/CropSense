import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from db.models import (
    get_stats,
    get_recent_detections,
    get_disease_frequency,
    get_daily_trend,
    get_risk_distribution,
)

st.set_page_config(
    page_title="Rythu Mitra — Analytics",
    page_icon="🌱",
    layout="wide"
)

# ─── Styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.hero {
    background: linear-gradient(135deg, #1D9E75 0%, #0F6E56 100%);
    padding: 2rem; border-radius: 16px;
    text-align: center; color: white; margin-bottom: 1.5rem;
}
.hero h1 { font-size: 2.2rem; font-weight: 700; margin: 0; }
.hero p  { opacity: 0.9; margin: 0.4rem 0 0; font-size: 1rem; }
.metric-card {
    background: var(--background-color);
    border: 1px solid rgba(128,128,128,0.2);
    border-radius: 14px; padding: 1.2rem;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ─── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🌱 Rythu Mitra Analytics</h1>
    <p>Real-time crop disease outbreak monitoring — Telangana</p>
</div>
""", unsafe_allow_html=True)

# ─── Auto refresh ─────────────────────────────────────────────────────────────
if st.button("🔄 Refresh Data"):
    st.rerun()
st.caption(f"Data updates on each refresh")

# ─── Stats row ────────────────────────────────────────────────────────────────
stats = get_stats()
c1, c2, c3, c4 = st.columns(4)
c1.metric("🧑‍🌾 Total Scans",    stats["total"])
c2.metric("👨‍🌾 Farmers Helped",  stats["farmers"])
c3.metric("🦠 Diseases Found",   stats["diseases"])
c4.metric("📅 Scans This Week",  stats["week"])

st.divider()

# ─── Main content ─────────────────────────────────────────────────────────────
col1, col2 = st.columns([1.5, 1], gap="large")

with col1:
    st.subheader("📍 Detection Map — Telangana")
    detections = get_recent_detections(200)

    if detections:
        df = pd.DataFrame(detections)
        df_disease = df[df["is_healthy"] == False]
        df_healthy = df[df["is_healthy"] == True]

        fig_map = go.Figure()

        if not df_disease.empty:
            fig_map.add_trace(go.Scattermapbox(
                lat=df_disease["lat"],
                lon=df_disease["lon"],
                mode="markers",
                marker=dict(size=12, color="red", opacity=0.7),
                text=df_disease["disease_key"].str.replace("___", " — "),
                name="Disease detected",
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Location: %{customdata}<br>"
                    "Confidence: %{marker.color}<extra></extra>"
                ),
                customdata=df_disease["location_name"],
            ))

        if not df_healthy.empty:
            fig_map.add_trace(go.Scattermapbox(
                lat=df_healthy["lat"],
                lon=df_healthy["lon"],
                mode="markers",
                marker=dict(size=10, color="green", opacity=0.6),
                text=df_healthy["crop"],
                name="Healthy crop",
                hovertemplate=(
                    "<b>Healthy %{text}</b><br>"
                    "Location: %{customdata}<extra></extra>"
                ),
                customdata=df_healthy["location_name"],
            ))

        fig_map.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=17.8, lon=79.1),
                zoom=6.5,
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=420,
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="right",  x=1
            ),
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No detections yet. Send a crop photo to @rythumitra_bot to see data here!")

with col2:
    st.subheader("🦠 Top Diseases (Last 30 Days)")
    freq = get_disease_frequency(30)
    if freq:
        df_freq = pd.DataFrame(freq)
        fig_bar = px.bar(
            df_freq, x="count", y="disease",
            orientation="h",
            color="count",
            color_continuous_scale=["#E1F5EE", "#1D9E75", "#0F6E56"],
            labels={"count": "Detections", "disease": ""},
        )
        fig_bar.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No disease data yet.")

st.divider()

col3, col4 = st.columns(2, gap="large")

with col3:
    st.subheader("📈 Daily Scan Trend (Last 14 Days)")
    trend = get_daily_trend(14)
    if trend:
        df_trend = pd.DataFrame(trend)
        fig_line = px.line(
            df_trend, x="date",
            y=["total", "diseases"],
            markers=True,
            labels={"value": "Count", "date": "Date",
                    "variable": "Type"},
            color_discrete_map={
                "total":    "#1D9E75",
                "diseases": "#E24B4A",
            },
        )
        fig_line.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Not enough data for trend yet.")

with col4:
    st.subheader("⛅ Spread Risk Distribution")
    risk_dist = get_risk_distribution()
    if risk_dist:
        fig_pie = px.pie(
            names=list(risk_dist.keys()),
            values=list(risk_dist.values()),
            color=list(risk_dist.keys()),
            color_discrete_map={
                "High":   "#E24B4A",
                "Medium": "#EF9F27",
                "Low":    "#1D9E75",
            },
            hole=0.45,
        )
        fig_pie.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=-0.1),
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No risk data yet.")

st.divider()

# ─── Recent detections table ──────────────────────────────────────────────────
st.subheader("📋 Recent Detections")
if detections:
    df_table = pd.DataFrame(detections[:20])
    df_table["disease"] = df_table["disease_key"].str.replace(
        "___", " — ").str.replace("_", " ")
    df_table["status"] = df_table["is_healthy"].map(
        {True: "✅ Healthy", False: "🔴 Disease"})
    df_table["conf"] = df_table["confidence"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(
        df_table[["created_at", "status", "disease",
                  "conf", "risk_level", "location_name"]].rename(columns={
            "created_at":    "Time",
            "status":        "Status",
            "disease":       "Detection",
            "conf":          "Confidence",
            "risk_level":    "Risk",
            "location_name": "Location",
        }),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No detections logged yet.")

st.markdown("""
<div style='text-align:center; color:#999; font-size:0.82rem; padding:1.5rem 0 0.5rem'>
    Built by <b>Venu Enugula</b> ·
    <a href='https://github.com/Venuenugula/CropSense'>GitHub</a> ·
    Rythu Mitra — AI for Telangana Farmers
</div>
""", unsafe_allow_html=True)