import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Enterprise Logs Dashboard Report",
    layout="wide"
)
st.page_link(
    "streamlit_frontend.py",
    label="⬅ Back to Console",
    icon="💬"
)
# -----------------------------------
# CSS
# -----------------------------------

st.markdown("""
<style>

.main {
    background-color: #0f172a;
}

.kpi-card {
    background: #1e293b;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    border: 1px solid #334155;
}

.kpi-label {
    color: #94a3b8;
    font-size: 14px;
}

.kpi-value {
    color: white;
    font-size: 30px;
    font-weight: bold;
}

.section-card {
    background: #1e293b;
    padding: 20px;
    border-radius: 12px;
    margin-top: 15px;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------------
# HEADER
# -----------------------------------

st.title("Enterprise Logs Dashboard Report")

# -----------------------------------
# KPI CARDS
# -----------------------------------

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Errors This Month</div>
        <div class="kpi-value">245</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Incidents This Month</div>
        <div class="kpi-value">876</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Affected Users</div>
        <div class="kpi-value">102</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Critical Incidents</div>
        <div class="kpi-value">56</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Worst Module</div>
        <div class="kpi-value">CardService</div>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------
# CHARTS
# -----------------------------------

left, right = st.columns(2)

with left:

    pie_df = pd.DataFrame({
        "Module": ["Card", "API", "Database", "User", "Network"],
        "Count": [35, 25, 15, 15, 10]
    })

    fig = px.pie(
        pie_df,
        names="Module",
        values="Count",
        title="Incident Distribution by Module"
    )

    st.plotly_chart(fig, use_container_width=True)

with right:

    bubble_df = pd.DataFrame({
        "Event": [
            "Card Failure",
            "API Timeout",
            "DB Deadlock",
            "Auth Error",
            "Network Failure"
        ],
        "Count": [145, 124, 98, 84, 62]
    })

    fig = px.scatter(
        bubble_df,
        x="Count",
        y="Event",
        size="Count",
        color="Count",
        title="Top 5 Critical Incidents"
    )

    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------
# TOP INCIDENTS
# -----------------------------------

st.subheader("🔥 Top 5 Incidents")

top_incidents = pd.DataFrame({
    "Event": [
        "Card Failure",
        "API Timeout",
        "DB Deadlock",
        "User Authentication Error",
        "Network Failure"
    ],
    "Count": [145, 124, 98, 84, 62]
})

st.dataframe(top_incidents, use_container_width=True)

# -----------------------------------
# CRITICAL INCIDENTS
# -----------------------------------

st.subheader("🚨 Critical Incidents")

critical_df = pd.DataFrame({
    "Timestamp": [
        "2026-06-07 10:23",
        "2026-06-07 09:45"
    ],
    "Event": [
        "Card Failure",
        "DB Deadlock"
    ],
    "UserId": [
        "USR101",
        "USR145"
    ],
    "CorrelationId": [
        "CORR7788",
        "CORR8891"
    ]
})

st.dataframe(
    critical_df,
    use_container_width=True
)

# -----------------------------------
# MONITORING LOGS
# -----------------------------------

st.subheader("📡 Monitoring Logs")

logs_df = pd.DataFrame({
    "Timestamp": [
        "2026-06-07 10:20",
        "2026-06-07 10:19"
    ],
    "Module": [
        "CardService",
        "UserService"
    ],
    "Level": [
        "ERROR",
        "INFO"
    ],
    "Event": [
        "Card Failure",
        "Login Success"
    ]
})

st.dataframe(
    logs_df,
    use_container_width=True
)

# -----------------------------------
# TREND CHART
# -----------------------------------

st.subheader("📈 Incident Trends")

trend_df = pd.DataFrame({
    "Module": [
        "User",
        "Card",
        "API",
        "DB",
        "Network"
    ],
    "Count": [
        20,
        145,
        124,
        98,
        62
    ]
})

fig = px.line(
    trend_df,
    x="Module",
    y="Count",
    markers=True
)

st.plotly_chart(
    fig,
    use_container_width=True
)