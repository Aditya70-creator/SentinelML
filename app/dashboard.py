import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import joblib
import pandas as pd
import streamlit as st
from api.main import NetworkFlowInput, check_drift, compute_shap_values, health_check, predict_flow
from src.data.generate_data import FEATURES
from src.monitoring.drift import evaluate_data_drift

st.set_page_config(page_title="SentinelML Dashboard", layout="wide")
st.title("🛡️ SentinelML — Network Intrusion Detection & MLOps Platform")

if not os.path.exists("models/sentinel_pipeline.joblib") or not os.path.exists("data/raw/network_flows_reference.csv"):
    with st.spinner("Initializing telemetry dataset and training models..."):
        from src.data.generate_data import generate_network_flows
        from src.models.train import train_and_evaluate
        os.makedirs("data/raw", exist_ok=True)
        generate_network_flows(n_samples=6000, drift=False, seed=42).to_csv("data/raw/network_flows_reference.csv", index=False)
        generate_network_flows(n_samples=1500, drift=True, seed=99).to_csv("data/raw/network_flows_drifted.csv", index=False)
        train_and_evaluate()

with open("models/metadata.json", "r") as f:
    meta = json.load(f)
pipeline = joblib.load("models/sentinel_pipeline.joblib")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Model Leaderboard & Metrics",
    "🔍 Live XAI Traffic Inspector",
    "📉 Data Drift & MLOps Monitor",
    "📡 Interactive REST API Playground"
])

with tab1:
    st.subheader(f"Active Production Model: `{meta['winning_model']}` (Optimal Threshold: `{meta['optimal_threshold']}`)")
    lb_df = pd.DataFrame(meta["leaderboard"]).T.drop(columns=["confusion_matrix"])
    st.dataframe(lb_df, use_container_width=True)

with tab2:
    st.subheader("Inspect Single Network Flow & SHAP Feature Impact")
    cols = st.columns(3)
    defaults = [1450.0, 52.0, 3.0, 820.0, 7.0, 3.0, 74000.0, 4.0, 0.82]
    user_input = {}
    for idx, feat in enumerate(FEATURES):
        user_input[feat] = cols[idx % 3].number_input(feat, value=float(defaults[idx]))

    if st.button("Classify Traffic & Explain with SHAP"):
        df_in = pd.DataFrame([user_input])[FEATURES]
        prob = float(pipeline.predict_proba(df_in)[0, 1])
        is_attack = prob >= meta["optimal_threshold"]

        if is_attack:
            st.error(f"🚨 INTRUSION DETECTED — Malicious Risk Score: {prob:.2%}")
        else:
            st.success(f"✅ BENIGN TRAFFIC — Malicious Risk Score: {prob:.2%}")

        X_trans = pipeline.named_steps["preprocessor"].transform(df_in)
        vals = compute_shap_values(pipeline.named_steps["classifier"], X_trans)
        shap_df = pd.DataFrame({"Feature": FEATURES, "SHAP Impact": vals}).set_index("Feature")
        st.bar_chart(shap_df)

with tab3:
    st.subheader("Production Covariate Shift & Retraining Trigger")
    batch_choice = st.radio("Select Incoming Traffic Batch:", ["Drifted Attack Surge Batch", "Stable Reference Batch"])
    ref_df = pd.read_csv("data/raw/network_flows_reference.csv")
    cur_df = pd.read_csv("data/raw/network_flows_drifted.csv" if "Drifted" in batch_choice else "data/raw/network_flows_reference.csv")
    report = evaluate_data_drift(ref_df, cur_df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Drifted Features", f"{report['drifted_feature_count']} / {report['total_features']}")
    c2.metric("Drift Share", f"{report['drift_share']:.1%}")
    c3.metric("Retraining Status", "🚨 RETRAIN TRIGGERED" if report["retrain_triggered"] else "✅ STABLE")
    st.dataframe(pd.DataFrame(report["features"]).T, use_container_width=True)

with tab4:
    st.subheader("📡 FastAPI Endpoint Simulator (Live Schema & JSON Response)")
    endpoint = st.selectbox("Select FastAPI Endpoint to Test:", [
        "POST /predict (Intrusion & SHAP Attribution)",
        "GET /health (Service & Model Readiness)",
        "GET /drift-status (KS-Test Telemetry JSON)"
    ])

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
            "dst_port_entropy": 0.82
        }
        raw_json = st.text_area("Request JSON Body (Pydantic Validated):", value=json.dumps(default_payload, indent=2), height=240)
        if st.button("Send POST /predict Request"):
            try:
                parsed = json.loads(raw_json)
                validated_input = NetworkFlowInput(**parsed)
                response = predict_flow(validated_input)
                st.code(json.dumps(response, indent=2), language="json")
            except Exception as e:
                st.error(f"422 Unprocessable Entity / Validation Error: {e}")
    elif endpoint.startswith("GET /health"):
        if st.button("Send GET /health Request"):
            st.code(json.dumps(health_check(), indent=2), language="json")
    else:
        if st.button("Send GET /drift-status Request"):
            st.code(json.dumps(check_drift(use_drifted_batch=True), indent=2), language="json")