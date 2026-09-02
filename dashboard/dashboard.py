import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

# 1. Page Configuration
st.set_page_config(
    page_title="MineSentinel | Operations Control Center",
    page_icon="MS",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Modern Glassmorphism & SCADA Aesthetic CSS Injection
st.markdown("""
<style>
    /* Global Background and Typography */
    .stApp {
        background-color: #0d0f17;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #e2e8f0;
    }

    /* Suppress Streamlit menu & footer, but keep header/toolbar minimal
       (do NOT hide it entirely - that also hides the sidebar reopen control) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}
    header [data-testid="stDecoration"] {display: none;}
    header [data-testid="stStatusWidget"] {display: none;}

    /* Sidebar Dark Theming */
    section[data-testid="stSidebar"] {
        background-color: #121524 !important;
        border-right: 1px solid #1e2238;
    }
    section[data-testid="stSidebar"] > div {
        background-color: #121524 !important;
    }

    /* Style every known variant of the sidebar collapse/expand control so it
       never disappears - this was the reason the left column looked "gone" */
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarExpandButton"],
    button[data-testid="baseButton-headerNoPadding"],
    div[data-testid="stSidebarCollapsedControl"] button,
    div[data-testid="collapsedControl"] button {
        color: #e2e8f0 !important;
        background-color: #161a2e !important;
        border: 1px solid #232845 !important;
        border-radius: 8px !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    div[data-testid="stSidebarCollapsedControl"],
    div[data-testid="collapsedControl"] {
        display: block !important;
        visibility: visible !important;
    }

    /* KPI Cards Styling */
    .kpi-card {
        padding: 24px;
        border-radius: 18px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 140px;
        margin-bottom: 15px;
    }

    .card-purple {
        background: linear-gradient(135deg, #a855f7 0%, #7e22ce 100%);
        color: #ffffff;
    }

    .card-cyan {
        background: linear-gradient(135deg, #06b6d4 0%, #0e7490 100%);
        color: #ffffff;
    }

    .card-dark {
        background-color: #161a2e;
        border: 1px solid #232845;
        color: #e2e8f0;
    }

    .kpi-title {
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        opacity: 0.85;
    }

    .kpi-value {
        font-size: 34px;
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }

    .kpi-badge {
        font-size: 11px;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        align-self: flex-start;
        background: rgba(255, 255, 255, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# 3. Sidebar Navigation
with st.sidebar:
    st.markdown("### MINESENTINEL")
    st.caption("TACTICAL LIFE-SAFETY PLATFORM")
    st.markdown("---")

    st.markdown("##### NAVIGATION")
    selected_page = st.radio(
        "Select View",
        options=["Live Operations", "Incident History", "Telemetry Config"],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("##### SENSOR MESH")
    st.markdown("**Zone 4 Mesh:** ONLINE")
    st.markdown("**Gateway 01:** SYNCING")
    st.markdown("**LLM Diagnostic:** READY")

# 4. Backend Communication
BACKEND_URL = "http://127.0.0.1:8000/api/dashboard-data"


def fetch_data():
    """Fetches real-time telemetry buffer and incident reports from FastAPI backend."""
    try:
        response = requests.get(BACKEND_URL, timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Telemetry Link Offline: {e}")
    return None


# 5. View Routing

if selected_page == "Live Operations":

    # Using st.fragment so only this block auto-refreshes every 2 seconds.
    # A full st.rerun() loop re-executes the ENTIRE script (including the
    # sidebar) on every cycle, which is what was causing the left column
    # to flicker / appear to vanish. Isolating the live view in a fragment
    # keeps the sidebar stable while data still updates.
    @st.fragment(run_every=2)
    def live_operations_view():
        data = fetch_data()

        if not data or not data.get("telemetry_history"):
            st.info("Awaiting live telemetry packets from Sector-4 Mesh Network...")
            return

        history = data["telemetry_history"]
        latest = history[-1]
        df_history = pd.DataFrame(history)
        df_history["time_label"] = pd.to_datetime(df_history["timestamp"], unit="s").dt.strftime("%H:%M:%S")

        # Top Header Bar
        col_head1, col_head2 = st.columns([3, 1])
        with col_head1:
            st.markdown("<h2 style='margin-bottom: 2px;'>Sector-4 Tactical Operations</h2>", unsafe_allow_html=True)
            st.caption("Live Telemetry Mesh & Real-time AI Hazard Mitigation")
        with col_head2:
            st.markdown(
                f"<div style='text-align: right; padding-top: 10px;'>"
                f"<span style='background-color: #1e293b; padding: 6px 14px; border-radius: 20px; "
                f"font-weight: bold; color: #38bdf8; font-size: 12px;'>"
                f"LAST SYNC: {df_history['time_label'].iloc[-1]}</span></div>",
                unsafe_allow_html=True
            )

        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

        # KPI Metric Cards
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            gas_val = latest['gas_ppm']
            st.markdown(f"""
            <div class="kpi-card card-purple">
                <div class="kpi-title">Gas Concentration</div>
                <div class="kpi-value">{gas_val:.1f} <span style="font-size: 16px;">PPM</span></div>
                <div class="kpi-badge">{"CRITICAL" if gas_val >= 400 else "NORMAL"}</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            accel_val = latest['accel_g']
            st.markdown(f"""
            <div class="kpi-card card-cyan">
                <div class="kpi-title">Impact Magnitude</div>
                <div class="kpi-value">{accel_val:.2f} <span style="font-size: 16px;">g</span></div>
                <div class="kpi-badge">{"IMPACT DETECTED" if accel_val > 1.5 else "STABLE"}</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            risk_lvl = latest['risk_level']
            risk_color = "#f43f5e" if risk_lvl == "CRITICAL" else "#eab308" if risk_lvl == "MEDIUM" else "#10b981"
            st.markdown(f"""
            <div class="kpi-card card-dark">
                <div class="kpi-title">AI Safety Assessment</div>
                <div class="kpi-value" style="color: {risk_color}; font-size: 30px;">{risk_lvl}</div>
                <div class="kpi-badge" style="background: rgba(255,255,255,0.08);">Score: {latest['rule_risk_score']:.1f}</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="kpi-card card-dark">
                <div class="kpi-title">Ingestion Buffer</div>
                <div class="kpi-value" style="font-size: 32px;">{len(history)} <span style="font-size: 16px;">pkts</span></div>
                <div class="kpi-badge" style="background: #0ea5e9;">100% INGESTION</div>
            </div>
            """, unsafe_allow_html=True)

        # Active Crisis Notification
        incident_data = data.get("latest_incident") or {}
        emergency_report = incident_data.get("report")
        if emergency_report:
            st.error("CRITICAL INCIDENT REPORT DISPATCHED BY AI AGENT")
            with st.expander("View AI Emergency Incident Report & Action Protocol", expanded=True):
                st.markdown(emergency_report)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # Dynamic Spline Waveform & Donut Ratio
        chart_left, chart_right = st.columns([2, 1])

        with chart_left:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=df_history["time_label"],
                y=df_history["gas_ppm"],
                mode='lines+markers',
                name='Gas PPM',
                line=dict(color='#a855f7', width=3, shape='spline'),
                fill='tozeroy',
                fillcolor='rgba(168, 85, 247, 0.15)'
            ))
            fig_trend.update_layout(
                title="Gas Concentration Spline Waveform (PPM)",
                template="plotly_dark",
                paper_bgcolor="#161a2e",
                plot_bgcolor="#161a2e",
                height=340,
                margin=dict(l=20, r=20, t=45, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                font=dict(family="Inter, sans-serif", color="#94a3b8")
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        with chart_right:
            risk_counts = df_history['risk_level'].value_counts()
            fig_donut = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                hole=0.68,
                title="Risk Classification Ratio",
                color_discrete_sequence=['#f43f5e', '#06b6d4', '#a855f7', '#10b981']
            )
            fig_donut.update_layout(
                template="plotly_dark",
                paper_bgcolor="#161a2e",
                plot_bgcolor="#161a2e",
                height=340,
                margin=dict(l=20, r=20, t=45, b=20),
                font=dict(family="Inter, sans-serif", color="#94a3b8")
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        # Bar Chart & Raw Telemetry Stream
        bottom_col1, bottom_col2 = st.columns([1, 1])

        with bottom_col1:
            fig_bar = px.bar(
                df_history.tail(15),
                x="time_label",
                y="accel_g",
                title="Recent Impact Vibrations (g)",
                labels={"time_label": "Time", "accel_g": "Magnitude (g)"},
                color="accel_g",
                color_continuous_scale=["#06b6d4", "#a855f7", "#f43f5e"]
            )
            fig_bar.update_layout(
                template="plotly_dark",
                paper_bgcolor="#161a2e",
                plot_bgcolor="#161a2e",
                height=260,
                margin=dict(l=20, r=20, t=45, b=20),
                coloraxis_showscale=False,
                font=dict(family="Inter, sans-serif", color="#94a3b8")
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with bottom_col2:
            st.markdown(
                "<p style='font-weight: 600; font-size: 15px; color: #cbd5e1; margin-top: 10px;'>"
                "Live Telemetry Stream (Raw Tail)</p>",
                unsafe_allow_html=True
            )
            st.dataframe(
                df_history[["time_label", "gas_ppm", "accel_g", "risk_level", "is_anomaly"]].tail(5),
                use_container_width=True,
                hide_index=True
            )

    live_operations_view()

elif selected_page == "Incident History":
    st.markdown("## AI Incident Logs & Disaster Protocol Archive")
    st.caption("Comprehensive log of detected anomalies and autonomous emergency assessments.")

    data = fetch_data()
    incident_data = (data.get("latest_incident") if data else {}) or {}
    emergency_report = incident_data.get("report")
    incident_timestamp = incident_data.get("timestamp")

    if emergency_report:
        formatted_time = (
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(incident_timestamp))
            if incident_timestamp else 'N/A'
        )
        st.markdown(f"**Incident Timestamp:** `{formatted_time}`")
        st.markdown(emergency_report)
    else:
        st.info("No recorded emergency incident reports in the active runtime buffer.")

elif selected_page == "Telemetry Config":
    st.markdown("## Sensor Node & Safety Threshold Configuration")
    st.caption("Configure industrial safety triggers for autonomous local alarms.")

    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        st.number_input("Combustible Gas Hazard Threshold (PPM)", value=400, min_value=100, max_value=2000)
        st.number_input("Impact G-Force Threshold (g)", value=1.5, min_value=0.5, max_value=10.0, step=0.1)
    with col_cfg2:
        st.number_input("Sensor Sampling Interval (seconds)", value=2, min_value=1, max_value=30)
        st.selectbox("Emergency Buzzer Profile", ["Continuous Siren", "High-Pitch Intermittent", "Silent Broadcast"])

    st.button("Save Local Configuration", use_container_width=True)