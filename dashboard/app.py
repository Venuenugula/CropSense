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
    get_hotspots,
    get_feedback_summary,
    get_interventions,
    create_intervention,
)

st.set_page_config(
    page_title="Rythu Mitra — Field Intelligence",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Plotly text styling (matches dashboard CSS)
_CHART_FONT = dict(family="Inter, Segoe UI, system-ui, sans-serif", color="#142718", size=13)
_CHART_PAPER = "rgba(255,255,255,0.92)"
_CHART_PLOT = "#fafcf9"


def _style_chart(fig):
    """Consistent typography, surfaces, and readable axes (cartesian charts)."""
    fig.update_layout(
        font=_CHART_FONT,
        paper_bgcolor=_CHART_PAPER,
        plot_bgcolor=_CHART_PLOT,
        title=dict(
            font=dict(size=15, color="#145a2a", family="Inter, Segoe UI, sans-serif"),
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(20, 39, 24, 0.09)",
            zeroline=False,
            linecolor="#c8dcc9",
            tickfont=dict(color="#142718"),
            title=dict(font=dict(color="#145a2a", size=12)),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(20, 39, 24, 0.09)",
            zeroline=False,
            linecolor="#c8dcc9",
            tickfont=dict(color="#142718"),
            title=dict(font=dict(color="#145a2a", size=12)),
        ),
        legend=dict(
            font=dict(color="#142718", size=12),
            bgcolor="rgba(255,255,255,0.82)",
            bordercolor="#c8dcc9",
            borderwidth=1,
        ),
    )
    return fig


# ─── Harvestiq-inspired design system (agritech) ─────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,400..800;1,14..32,400..800&display=swap');

:root {
  --rm-green: #1f8b3e;
  --rm-green-deep: #145a2a;
  --rm-green-soft: #eaf6ed;
  --rm-accent: #2ea156;
  --rm-cream: #f4faf5;
  --rm-text: #0f1f12;
  --rm-muted: #4a6350;
  --rm-border: #c8dcc9;
  --rm-danger: #b3261e;
  --rm-warn: #b87208;
  --rm-shadow: 0 14px 40px rgba(15, 31, 18, 0.09);
  --rm-radius: 16px;
  --rm-radius-sm: 12px;
}

html, body {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
  color: var(--rm-text) !important;
  -webkit-font-smoothing: antialiased;
}

/* Main column: always dark body text on light background (fixes theme white text bleed) */
[data-testid="stMain"],
[data-testid="stMain"] [data-testid="stVerticalBlock"],
[data-testid="stMarkdownContainer"] {
  color: var(--rm-text) !important;
}
[data-testid="stMain"] input,
[data-testid="stMain"] textarea {
  color: var(--rm-text) !important;
  caret-color: var(--rm-text) !important;
}
/* Select / date widgets (Base Web) — keep value text dark on light panels */
[data-testid="stMain"] [data-baseweb="select"] > div,
[data-testid="stMain"] [data-baseweb="input"] input {
  color: var(--rm-text) !important;
}
[data-testid="stMain"] [data-baseweb="datepicker"] input {
  color: var(--rm-text) !important;
}

.block-container {
  padding-top: 1.25rem;
  padding-bottom: 2rem;
  max-width: 1280px;
}

[data-testid="stAppViewContainer"] {
  background: radial-gradient(ellipse 140% 90% at 100% -20%, #dff0e3 0%, var(--rm-cream) 38%, #eef5ef 100%) !important;
}

.hero {
  background: linear-gradient(128deg, #1f8b3e 0%, #166c30 42%, #0d4a24 100%);
  padding: 2.25rem 2rem;
  border-radius: 20px;
  margin-bottom: 1.25rem;
  box-shadow: var(--rm-shadow);
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 18% 20%, rgba(255,255,255,0.14) 0%, transparent 45%),
              radial-gradient(circle at 88% 80%, rgba(255,255,255,0.08) 0%, transparent 40%);
  pointer-events: none;
}
.hero-inner { position: relative; z-index: 1; }
.hero-badge {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.95) !important;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.22);
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  margin-bottom: 0.85rem;
}
.hero h1 {
  font-size: clamp(1.65rem, 3.2vw, 2.35rem);
  font-weight: 800;
  margin: 0;
  color: #ffffff !important;
  letter-spacing: -0.02em;
  line-height: 1.15;
}
.hero .hero-lead {
  opacity: 0.96;
  margin: 0.65rem 0 0;
  font-size: 1.08rem;
  font-weight: 600;
  line-height: 1.45;
  color: #ffffff !important;
  max-width: 46rem;
  text-shadow: 0 1px 18px rgba(0,0,0,0.12);
}
.hero .hero-sub {
  opacity: 0.9;
  margin: 0.55rem 0 0;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.45;
  color: #e8f7eb !important;
}

[data-testid="stHeader"] { font-weight: 700 !important; color: var(--rm-text) !important; }
/* Section titles (Streamlit subheader = h3) */
h3 {
  font-size: 1.08rem !important;
  font-weight: 750 !important;
  color: var(--rm-green-deep) !important;
  letter-spacing: -0.02em !important;
  line-height: 1.35 !important;
  margin: 0.35rem 0 0.85rem 0 !important;
  padding: 0.35rem 0 0.5rem 0.85rem !important;
  border-left: 4px solid var(--rm-green) !important;
  border-bottom: 1px solid var(--rm-border) !important;
  background: linear-gradient(90deg, rgba(234,246,237,0.65) 0%, transparent 65%);
  border-radius: 0 var(--rm-radius-sm) var(--rm-radius-sm) 0 !important;
}

[data-testid="stCaptionContainer"] {
  color: var(--rm-muted) !important;
  font-weight: 500 !important;
  font-size: 0.88rem !important;
}
[data-testid="stCaptionContainer"] p { color: var(--rm-muted) !important; }

[data-testid="stMarkdownContainer"] p {
  color: var(--rm-text) !important;
}
[data-testid="stMarkdownContainer"] li {
  color: var(--rm-text) !important;
}

[data-testid="stWidgetLabel"] p {
  color: var(--rm-green-deep) !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
}

/* Data tables — readable body text */
[data-testid="stDataFrame"] { color: var(--rm-text) !important; }

div[data-testid="stMetric"] {
  background: #fff !important;
  border: 1px solid var(--rm-border) !important;
  border-radius: var(--rm-radius) !important;
  padding: 1rem 1.1rem !important;
  box-shadow: var(--rm-shadow) !important;
}
[data-testid="stMetricLabel"] { color: var(--rm-muted) !important; font-weight: 600 !important; font-size: 0.82rem !important; }
[data-testid="stMetricValue"] { color: var(--rm-green-deep) !important; font-weight: 800 !important; }

hr, [data-testid="stHorizontalRule"] {
  border: none !important;
  height: 1px !important;
  background: linear-gradient(90deg, transparent, var(--rm-border), transparent) !important;
  margin: 1.35rem 0 !important;
}

[data-testid="stSidebar"] { border-right: 1px solid var(--rm-border); }

.stDownloadButton button, div[data-testid="stButton"] > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  border: 1px solid var(--rm-border) !important;
}
.stDownloadButton button {
  background: linear-gradient(140deg, var(--rm-green), var(--rm-accent)) !important;
  color: #fff !important;
  border: none !important;
}

div[data-testid="stExpander"] details, .stAlert {
  border-radius: 12px !important;
  border-color: var(--rm-border) !important;
}

[data-testid="stNotification"], .stAlert {
  color: var(--rm-text) !important;
}
div[data-testid="stAlertContentSuccess"],
div[data-testid="stAlertContentInfo"] {
  color: var(--rm-text) !important;
}
div[data-testid="stAlertContentSuccess"] *,
div[data-testid="stAlertContentInfo"] * {
  color: var(--rm-text) !important;
}
div[data-testid="stAlertContentSuccess"] {
  background: linear-gradient(90deg, #eaf6ed, #f6faf6) !important;
  border-left: 4px solid var(--rm-green) !important;
}
div[data-testid="stAlertContentInfo"] {
  background: #f5faf6 !important;
  border-left: 4px solid var(--rm-accent) !important;
}

.footer-rm {
  text-align: center;
  color: var(--rm-muted);
  font-size: 0.82rem;
  padding: 1.75rem 0 0.5rem;
  border-top: 1px solid var(--rm-border);
  margin-top: 1.5rem;
}
.footer-rm a { color: var(--rm-green); font-weight: 600; text-decoration: none; }
.footer-rm a:hover { text-decoration: underline; }
</style>
""",
    unsafe_allow_html=True,
)

# ─── Hero ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero">
  <div class="hero-inner">
    <span class="hero-badge">Telangana · Crop health command center</span>
    <h1>🌱 See outbreaks before they spread</h1>
    <p class="hero-lead">One dashboard for disease signals, weather-risk context, and officer-ready actions — built for real field ops.</p>
    <p class="hero-sub">From farmer photo → district hotspot → intervention log — fewer surprises, faster response</p>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── Toolbar ─────────────────────────────────────────────────────────────────
_tool_l, _tool_r = st.columns([4, 1])
with _tool_l:
    st.caption("Data refreshes when you load this page or tap **Refresh**.")
with _tool_r:
    if st.button("🔄 Refresh data", type="primary", width="stretch"):
        st.rerun()

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
            cd_dis = list(
                zip(
                    df_disease["location_name"].astype(str),
                    df_disease["confidence"].astype(float),
                )
            )
            fig_map.add_trace(
                go.Scattermap(
                    lat=df_disease["lat"],
                    lon=df_disease["lon"],
                    mode="markers",
                    marker=dict(size=12, color="#c53929", opacity=0.82),
                    text=df_disease["disease_key"].str.replace("___", " — "),
                    name="Disease detected",
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "Location: %{customdata[0]}<br>"
                        "Confidence: %{customdata[1]:.1f}%<extra></extra>"
                    ),
                    customdata=cd_dis,
                )
            )

        if not df_healthy.empty:
            fig_map.add_trace(
                go.Scattermap(
                    lat=df_healthy["lat"],
                    lon=df_healthy["lon"],
                    mode="markers",
                    marker=dict(size=10, color="#1f8b3e", opacity=0.65),
                    text=df_healthy["crop"],
                    name="Healthy crop",
                    hovertemplate=(
                        "<b>Healthy %{text}</b><br>"
                        "Location: %{customdata}<extra></extra>"
                    ),
                    customdata=df_healthy["location_name"].astype(str).tolist(),
                )
            )

        fig_map.update_layout(
            map=dict(
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
        _style_chart(fig_map)
        st.plotly_chart(fig_map, width="stretch")
    else:
        st.info("No detections yet. Send a crop photo to @rythumitra_bot to see data here!")

with col2:
    st.subheader("🦠 Top Diseases (Last 30 Days)")
    freq = get_disease_frequency(30)
    if freq:
        df_freq = pd.DataFrame(freq)
        df_freq["count"] = pd.to_numeric(df_freq["count"], errors="coerce").fillna(0).astype(int)
        fig_bar = px.bar(
            df_freq,
            x="count",
            y="disease",
            orientation="h",
            color="count",
            color_continuous_scale=["#eaf6ed", "#1f8b3e", "#166c30"],
            labels={"count": "Detections", "disease": "Disease / condition"},
            hover_data=["crop"],
        )
        fig_bar.update_layout(
            height=max(400, min(520, 80 + len(df_freq) * 28)),
            margin=dict(l=8, r=12, t=36, b=48),
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed", title=dict(text="")),
            xaxis_title="Detections",
        )
        _style_chart(fig_bar)
        st.plotly_chart(fig_bar, width="stretch")
    else:
        st.info("No disease data yet.")

st.divider()

col3, col4 = st.columns(2, gap="large")

with col3:
    st.subheader("📈 Daily Scan Trend (Last 14 Days)")
    trend = get_daily_trend(14)
    if trend:
        df_trend = pd.DataFrame(trend)
        df_trend["total"] = pd.to_numeric(df_trend["total"], errors="coerce").fillna(0)
        df_trend["diseases"] = pd.to_numeric(df_trend["diseases"], errors="coerce").fillna(0)
        df_trend["date"] = pd.to_datetime(df_trend["date"], errors="coerce")
        df_trend = df_trend.dropna(subset=["date"]).sort_values("date")
        if df_trend.empty:
            st.info("Not enough valid dates for trend yet.")
        else:
            fig_line = px.line(
                df_trend,
                x="date",
                y=["total", "diseases"],
                markers=True,
                labels={
                    "value": "Count",
                    "date": "Date",
                    "variable": "Metric",
                },
                color_discrete_map={
                    "total": "#1f8b3e",
                    "diseases": "#c53929",
                },
            )
            _names = {
                "total": "All scans",
                "diseases": "Disease detections",
            }
            fig_line.for_each_trace(
                lambda tr: tr.update(name=_names.get(tr.name, tr.name))
            )
            fig_line.update_layout(
                height=340,
                margin=dict(l=8, r=12, t=28, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title="Date",
                yaxis_title="Count",
            )
            fig_line.update_xaxes(tickformat="%b %d")
            _style_chart(fig_line)
            st.plotly_chart(fig_line, width="stretch")
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
                "High":   "#c53929",
                "Medium": "#d08808",
                "Low":    "#1f8b3e",
            },
            hole=0.45,
        )
        fig_pie.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=-0.1),
        )
        _style_chart(fig_pie)
        st.plotly_chart(fig_pie, width="stretch")
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
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No detections logged yet.")

st.divider()

# ─── Official hotspot dashboard ───────────────────────────────────────────────
st.subheader("🛡️ Official Hotspot Dashboard")
hcol1, hcol2 = st.columns([2, 1], gap="large")

with hcol1:
    hotspots = get_hotspots(days=7, min_cases=2)
    if hotspots:
        df_hot = pd.DataFrame(hotspots)
        df_hot["disease"] = df_hot["disease_key"].str.replace("___", " — ").str.replace("_", " ")
        df_hot["cases"] = pd.to_numeric(df_hot["cases"], errors="coerce").fillna(0).astype(int)
        df_hot["avg_confidence"] = pd.to_numeric(df_hot["avg_confidence"], errors="coerce").fillna(0)
        df_hot["avg_risk"] = pd.to_numeric(df_hot["avg_risk"], errors="coerce").fillna(0)
        fig_hot = px.scatter(
            df_hot,
            x="cases",
            y="avg_risk",
            size="avg_confidence",
            color="disease",
            size_max=26,
            hover_name="location_name",
            hover_data={
                "disease": True,
                "cases": True,
                "avg_confidence": ":.1f",
                "avg_risk": ":.2f",
                "disease_key": False,
                "location_name": False,
            },
            labels={
                "cases": "Cases (7 days)",
                "avg_risk": "Avg risk score",
                "avg_confidence": "Avg confidence",
                "disease": "Disease",
            },
            title="Hotspots: volume vs risk (bubble size = avg confidence)",
        )
        fig_hot.update_layout(
            margin=dict(l=8, r=12, t=48, b=40),
        )
        _style_chart(fig_hot)
        st.plotly_chart(fig_hot, width="stretch")
        st.dataframe(
            df_hot[["location_name", "disease", "cases", "avg_confidence", "avg_risk"]],
            width="stretch",
            hide_index=True,
        )
        st.download_button(
            "⬇️ Export Hotspots CSV",
            data=df_hot.to_csv(index=False).encode("utf-8"),
            file_name="hotspots_report.csv",
            mime="text/csv",
            width="stretch",
        )
    else:
        st.info("No hotspots detected for selected thresholds yet.")

with hcol2:
    st.markdown("#### ➕ Log Intervention")
    with st.form("intervention_form", clear_on_submit=True):
        i_district = st.text_input("District", value="Warangal")
        i_disease = st.text_input("Disease Key", value="Tomato___Late_blight")
        i_action = st.text_area("Action Plan", value="Field scouting + preventive spray advisory camp")
        i_owner = st.text_input("Owner", value="District Agri Officer")
        i_due = st.date_input("Due Date")
        i_status = st.selectbox("Status", ["planned", "in_progress", "completed"])
        i_notes = st.text_area("Notes", value="")
        if st.form_submit_button("Save Intervention"):
            create_intervention(
                district=i_district,
                disease_key=i_disease,
                action=i_action,
                owner=i_owner,
                due_date=str(i_due),
                status=i_status,
                notes=i_notes,
            )
            st.success("Intervention saved.")

st.markdown("#### 📌 Intervention Workflow")
interventions = get_interventions(100)
if interventions:
    df_int = pd.DataFrame(interventions)
    st.dataframe(
        df_int[["id", "district", "disease_key", "status", "owner", "due_date", "updated_at", "action", "notes"]],
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "⬇️ Export Interventions CSV",
        data=df_int.to_csv(index=False).encode("utf-8"),
        file_name="interventions_report.csv",
        mime="text/csv",
        width="stretch",
    )
else:
    st.info("No interventions logged yet.")

st.divider()

# ─── Model monitoring panel ───────────────────────────────────────────────────
st.subheader("🧪 Model Monitoring Panel")
m1, m2, m3 = st.columns(3)
feedback = get_feedback_summary(30)

if detections:
    df_recent = pd.DataFrame(detections)
    uncertain_rate = float((df_recent["confidence"] < 65).mean() * 100)
    avg_conf = float(df_recent["confidence"].mean())
else:
    uncertain_rate = 0.0
    avg_conf = 0.0

m1.metric("👍 Helpful Feedback Rate (30d)", f"{feedback['positive_rate']}%")
m2.metric("⚠️ Uncertain Prediction Rate", f"{uncertain_rate:.1f}%")
m3.metric("🎯 Avg Confidence (Recent)", f"{avg_conf:.1f}%")

if detections:
    df_recent["uncertain"] = df_recent["confidence"] < 65
    conf_fig = px.histogram(
        df_recent,
        x="confidence",
        nbins=20,
        title="Confidence Distribution (Recent Detections)",
        color_discrete_sequence=["#1f8b3e"],
    )
    _style_chart(conf_fig)
    st.plotly_chart(conf_fig, width="stretch")

st.markdown("""
<div class="footer-rm">
    Built by <b>Venu Enugula</b> ·
    <a href='https://github.com/Venuenugula/CropSense' target="_blank" rel="noopener">GitHub</a> ·
    Rythu Mitra — AI for Telangana farmers
</div>
""", unsafe_allow_html=True)