import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from api.main import (
    NetworkFlowInput,
    check_drift,
    compute_shap_values,
    health_check,
    predict_flow,
)
from src.data.generate_data import FEATURES
from src.monitoring.drift import evaluate_data_drift

st.set_page_config(
    page_title="SentinelML | SOC Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom Enterprise Cyber-SOC CSS ───
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top left, #0f172a 0%, #090d16 55%, #050811 100%);
        color: #f8fafc;
    }
    .soc-banner {
        background: linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(30,27,75,0.85) 100%);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-left: 5px solid #00f2fe;
        border-radius: 14px;
        padding: 22px 28px;
        margin-bottom: 22px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
    }
    .soc-title {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .soc-sub {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 6px;
    }
    .kpi-card {
        background: rgba(15, 23, 42, 0.78);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-top: 3px solid #38bdf8;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.3);
    }
    .kpi-label {
        color: #94a3b8;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
    }
    .kpi-value {
        color: #f8fafc;
        font-size: 1.65rem;
        font-weight: 800;
        margin-top: 4px;
    }
    .kpi-sub {
        color: #34d399;
        font-size: 0.78rem;
        margin-top: 2px;
    }
    .panel-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 4px;
    }
    .panel-caption {
        font-size: 0.82rem;
        color: #94a3b8;
        margin-bottom: 10px;
    }
    div[data-testid="stTabs"] button {
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Auto-bootstrap data and model on cloud if missing ───
if not os.path.exists("models/sentinel_pipeline.joblib") or not os.path.exists(
    "data/raw/network_flows_reference.csv"
):
    with st.spinner("Initializing telemetry dataset and training models..."):
        from src.data.generate_data import generate_network_flows
        from src.models.train import train_and_evaluate

        os.makedirs("data/raw", exist_ok=True)
        generate_network_flows(n_samples=6000, drift=False, seed=42).to_csv(
            "data/raw/network_flows_reference.csv", index=False
        )
        generate_network_flows(n_samples=1500, drift=True, seed=99).to_csv(
            "data/raw/network_flows_drifted.csv", index=False
        )
        train_and_evaluate()

with open("models/metadata.json", "r") as f:
    meta = json.load(f)
pipeline = joblib.load("models/sentinel_pipeline.joblib")
winner_name = meta["winning_model"]
winner_stats = meta["leaderboard"][winner_name]

# ─── Sidebar Command Panel ───
with st.sidebar:
    st.markdown("### 🛡️ SentinelML Control Node")
    st.caption("Explainable Network IDS & MLOps")
    st.divider()
    st.markdown("**🟢 Engine Status:** `ONLINE`")
    st.markdown(f"**🏆 Champion Model:** `{winner_name}`")
    st.markdown(f"**🎯 Decision Threshold:** `{meta['optimal_threshold']}`")
    st.markdown(f"**📈 Validation PR-AUC:** `{winner_stats['pr_auc']:.4f}`")
    st.divider()
    st.markdown("#### 🔬 Monitored Features (9)")
    for f_name in FEATURES:
        st.markdown(f"- `{f_name}`")
    st.divider()
    st.caption("Built by Aditya Mitra • KIIT CSE")

# ─── Top Hero Banner ───
st.markdown(
    """
    <div class="soc-banner">
        <div class="soc-title">🛡️ SentinelML — Cyber Defense & Explainable MLOps Center</div>
        <div class="soc-sub">
            Real-Time Network Flow Telemetry Classification • Cost-Sensitive Threshold Calibration • Local SHAP Attribution • KS-Test Covariate Shift Telemetry
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Top KPI Row ───
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-label">Active Production Model</div>
            <div class="kpi-value">{winner_name}</div>
            <div class="kpi-sub">✔ Leak-Free Pipeline</div>
        </div>""",
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f"""<div class="kpi-card" style="border-top-color:#34d399;">
            <div class="kpi-label">Held-Out PR-AUC Score</div>
            <div class="kpi-value">{winner_stats['pr_auc']*100:.2f}%</div>
            <div class="kpi-sub">▲ Outperforms Linear Baseline</div>
        </div>""",
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f"""<div class="kpi-card" style="border-top-color:#818cf8;">
            <div class="kpi-label">F1-Score / Precision</div>
            <div class="kpi-value">{winner_stats['f1_score']*100:.2f}%</div>
            <div class="kpi-sub">Precision: {winner_stats['precision']*100:.2f}%</div>
        </div>""",
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        f"""<div class="kpi-card" style="border-top-color:#fbbf24;">
            <div class="kpi-label">Calibrated Threshold</div>
            <div class="kpi-value">{meta['optimal_threshold']:.4f}</div>
            <div class="kpi-sub">Recall: {winner_stats['recall']*100:.2f}%</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.write("")

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🔍 Live XAI Traffic Inspector",
        "📊 Model Leaderboard & Diagnostics",
        "📉 Data Drift & MLOps Telemetry",
        "📡 Interactive REST API Playground",
    ]
)

# ═══════════════════════════════════════════════════════════
# TAB 1: LIVE XAI TRAFFIC INSPECTOR (Zero Text Overlap)
# ═══════════════════════════════════════════════════════════
with tab1:
    st.markdown("#### ⚡ Quick Traffic Scenario Presets")
    p_col1, p_col2, p_col3 = st.columns(3)

    if "preset_vals" not in st.session_state:
        st.session_state.preset_vals = [1450.0, 52.0, 3.0, 820.0, 7.0, 3.0, 74000.0, 4.0, 0.82]

    if p_col1.button("🚨 Load Volumetric DDoS Attack Preset", use_container_width=True):
        st.session_state.preset_vals = [1650.0, 64.0, 2.0, 940.0, 8.0, 4.0, 92000.0, 5.0, 0.89]
    if p_col2.button("🕵️ Load Stealth Port-Scan / Brute-Force", use_container_width=True):
        st.session_state.preset_vals = [410.0, 17.0, 11.0, 310.0, 5.0, 3.0, 21000.0, 6.0, 0.86]
    if p_col3.button("✅ Load Normal Benign HTTPS Flow", use_container_width=True):
        st.session_state.preset_vals = [240.0, 12.0, 14.0, 310.0, 1.0, 0.0, 16500.0, 0.0, 0.18]

    with st.expander("🎛️ Fine-Tune Network Flow Telemetry Features", expanded=True):
        cols = st.columns(3)
        user_input = {}
        for idx, feat in enumerate(FEATURES):
            user_input[feat] = cols[idx % 3].number_input(
                feat,
                value=float(st.session_state.preset_vals[idx]),
                key=f"inp_{feat}_{st.session_state.preset_vals[idx]}",
            )

    df_in = pd.DataFrame([user_input])[FEATURES]
    prob = float(pipeline.predict_proba(df_in)[0, 1])
    thresh = float(meta["optimal_threshold"])
    is_attack = prob >= thresh

    X_trans = pipeline.named_steps["preprocessor"].transform(df_in)
    vals = compute_shap_values(pipeline.named_steps["classifier"], X_trans)

    st.write("")
    g_col, s_col = st.columns([1, 1.4], gap="large")

    with g_col:
        st.markdown(
            '<div class="panel-header">🎯 Real-Time Threat Classification</div>'
            '<div class="panel-caption">Calibrated probability vs optimal PR threshold</div>',
            unsafe_allow_html=True,
        )
        if is_attack:
            st.error(
                f"🚨 **INTRUSION DETECTED** — Malicious Risk: **{prob:.2%}** (Threshold: `{thresh}`)"
            )
        else:
            st.success(
                f"✅ **BENIGN TRAFFIC** — Malicious Risk: **{prob:.2%}** (Threshold: `{thresh}`)"
            )

        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=prob * 100,
                number={"suffix": "%", "font": {"color": "#f8fafc", "size": 34}},
                gauge={
                    "axis": {
                        "range": [0, 100],
                        "tickwidth": 1,
                        "tickcolor": "#94a3b8",
                        "tickfont": {"size": 12, "color": "#cbd5e1"},
                    },
                    "bar": {"color": "#f43f5e" if is_attack else "#10b981"},
                    "bgcolor": "#0f172a",
                    "borderwidth": 1,
                    "bordercolor": "#334155",
                    "steps": [
                        {"range": [0, thresh * 100], "color": "rgba(16, 185, 129, 0.18)"},
                        {"range": [thresh * 100, 100], "color": "rgba(244, 63, 94, 0.22)"},
                    ],
                    "threshold": {
                        "line": {"color": "#fbbf24", "width": 4},
                        "thickness": 0.8,
                        "value": thresh * 100,
                    },
                },
            )
        )
        fig_gauge.update_layout(
            height=290,
            margin=dict(l=38, r=38, t=25, b=15),
            paper_bgcolor="rgba(0,0,0,0)",
            font={"color": "#f8fafc"},
        )
        st.plotly_chart(
            fig_gauge, use_container_width=True, config={"displayModeBar": False}
        )

    with s_col:
        st.markdown(
            '<div class="panel-header">🧠 Local SHAP Feature Attribution</div>'
            '<div class="panel-caption">Exact feature-level impact driving this individual prediction</div>',
            unsafe_allow_html=True,
        )
        shap_df = pd.DataFrame({"Feature": FEATURES, "SHAP_Impact": vals}).sort_values(
            by="SHAP_Impact", ascending=True
        )
        shap_df["Impact Direction"] = np.where(
            shap_df["SHAP_Impact"] >= 0,
            "Pushes toward Intrusion (+)",
            "Pushes toward Benign (-)",
        )
        fig_shap = px.bar(
            shap_df,
            x="SHAP_Impact",
            y="Feature",
            orientation="h",
            color="Impact Direction",
            color_discrete_map={
                "Pushes toward Intrusion (+)": "#f43f5e",
                "Pushes toward Benign (-)": "#38bdf8",
            },
        )
        fig_shap.update_layout(
            height=365,
            margin=dict(l=10, r=20, t=15, b=55),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,0.5)",
            font={"color": "#f8fafc", "size": 12},
            xaxis_title="SHAP Value (Impact on Model Output)",
            yaxis_title=None,
            legend=dict(
                title=None,
                orientation="h",
                yanchor="top",
                y=-0.18,
                xanchor="center",
                x=0.5,
                font=dict(size=12, color="#e2e8f0"),
            ),
        )
        st.plotly_chart(
            fig_shap, use_container_width=True, config={"displayModeBar": False}
        )

# ═══════════════════════════════════════════════════════════
# TAB 2: MODEL LEADERBOARD & DIAGNOSTICS
# ═══════════════════════════════════════════════════════════
with tab2:
    st.markdown("#### 🏆 Multi-Model Benchmark Comparison")
    lb_df = pd.DataFrame(meta["leaderboard"]).T.drop(columns=["confusion_matrix"])
    st.dataframe(lb_df.style.highlight_max(axis=0, color="#065f46"), use_container_width=True)

    c_left, c_right = st.columns([1.2, 1], gap="large")
    with c_left:
        st.markdown(
            '<div class="panel-header">📊 Metric Comparison Across Candidates</div>',
            unsafe_allow_html=True,
        )
        plot_df = (
            lb_df[["pr_auc", "f1_score", "precision", "recall"]]
            .reset_index()
            .melt(id_vars="index", var_name="Metric", value_name="Score")
        )
        fig_comp = px.bar(
            plot_df,
            x="Metric",
            y="Score",
            color="index",
            barmode="group",
            color_discrete_sequence=["#38bdf8", "#34d399", "#818cf8"],
        )
        fig_comp.update_layout(
            yaxis_range=[0.75, 1.0],
            margin=dict(l=10, r=10, t=15, b=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,0.5)",
            font={"color": "#f8fafc"},
            legend=dict(
                title=None, orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5
            ),
            height=360,
        )
        st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})

    with c_right:
        st.markdown(
            f'<div class="panel-header">🎯 Confusion Matrix — {winner_name}</div>',
            unsafe_allow_html=True,
        )
        cm = np.array(winner_stats["confusion_matrix"])
        fig_cm = px.imshow(
            cm,
            text_auto=True,
            color_continuous_scale="Blues",
            x=["Pred Benign (0)", "Pred Intrusion (1)"],
            y=["Actual Benign (0)", "Actual Intrusion (1)"],
        )
        fig_cm.update_layout(
            margin=dict(l=10, r=10, t=15, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            font={"color": "#f8fafc"},
            height=360,
        )
        st.plotly_chart(fig_cm, use_container_width=True, config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════
# TAB 3: DATA DRIFT & MLOPS TELEMETRY
# ═══════════════════════════════════════════════════════════
with tab3:
    st.markdown("#### 📉 Kolmogorov-Smirnov (`ks_2samp`) Covariate Shift Monitor")
    col_r1, col_r2 = st.columns([1, 1])
    batch_choice = col_r1.radio(
        "Select Incoming Telemetry Batch:",
        ["Drifted Attack Surge Batch", "Stable Reference Batch"],
        horizontal=True,
    )
    inspected_feat = col_r2.selectbox("Inspect Feature Distribution Overlay:", FEATURES)

    ref_df = pd.read_csv("data/raw/network_flows_reference.csv")
    cur_df = pd.read_csv(
        "data/raw/network_flows_drifted.csv"
        if "Drifted" in batch_choice
        else "data/raw/network_flows_reference.csv"
    )
    report = evaluate_data_drift(ref_df, cur_df)

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Drifted Features Flagged",
        f"{report['drifted_feature_count']} / {report['total_features']}",
    )
    m2.metric("Covariate Drift Share", f"{report['drift_share']:.1%}")
    m3.metric(
        "Pipeline Retraining Trigger",
        "🚨 RETRAIN REQUIRED" if report["retrain_triggered"] else "✅ MODEL STABLE",
    )

    dist_df = pd.concat(
        [
            pd.DataFrame(
                {inspected_feat: ref_df[inspected_feat].dropna(), "Dataset": "Reference Baseline"}
            ),
            pd.DataFrame(
                {inspected_feat: cur_df[inspected_feat].dropna(), "Dataset": "Incoming Batch"}
            ),
        ]
    )
    fig_dist = px.histogram(
        dist_df,
        x=inspected_feat,
        color="Dataset",
        barmode="overlay",
        nbins=45,
        histnorm="probability density",
        color_discrete_map={"Reference Baseline": "#38bdf8", "Incoming Batch": "#f43f5e"},
    )
    fig_dist.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.5)",
        font={"color": "#f8fafc"},
        legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False})

    st.dataframe(pd.DataFrame(report["features"]).T, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# TAB 4: INTERACTIVE REST API PLAYGROUND
# ═══════════════════════════════════════════════════════════
with tab4:
    st.markdown("#### 📡 FastAPI Endpoint Simulator (Pydantic Schema Validation)")
    endpoint = st.selectbox(
        "Select FastAPI Endpoint:",
        [
            "POST /predict (Intrusion & SHAP Attribution)",
            "GET /health (Service & Model Readiness)",
            "GET /drift-status (KS-Test Telemetry JSON)",
        ],
    )

    if endpoint.startswith("POST /predict"):
        default_payload = {
            "flow_duration_ms": 1450.5,
            "total_fwd_packets": 52,
            "total_bwd_packets": 3,
            "packet_length_mean": 820.0,
            "syn_flag_count": 7,
            "rst_flag_count": 3,
            "flow_bytes_per_sec": 74000.0,
            "failed_login_attempts": 4,
            "dst_port_entropy": 0.82,
        }
        raw_json = st.text_area(
            "Request JSON Body:", value=json.dumps(default_payload, indent=2), height=230
        )
        if st.button("🚀 Execute POST /predict"):
            try:
                parsed = json.loads(raw_json)
                validated_input = NetworkFlowInput(**parsed)
                response = predict_flow(validated_input)
                st.code(json.dumps(response, indent=2), language="json")
            except Exception as e:
                st.error(f"422 Unprocessable Entity / Validation Error: {e}")
    elif endpoint.startswith("GET /health"):
        if st.button("🚀 Execute GET /health"):
            st.code(json.dumps(health_check(), indent=2), language="json")
    else:
        if st.button("🚀 Execute GET /drift-status"):
            st.code(json.dumps(check_drift(use_drifted_batch=True), indent=2), language="json")