import json
import os
import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.data.generate_data import FEATURES
from src.monitoring.drift import evaluate_data_drift

app = FastAPI(
    title="SentinelML API",
    description="Explainable Network Intrusion Detection & MLOps Platform",
    version="1.0.0",
)

MODEL_PATH = "models/sentinel_pipeline.joblib"
META_PATH = "models/metadata.json"

class NetworkFlowInput(BaseModel):
    flow_duration_ms: float = Field(..., ge=0, json_schema_extra={"example": 1450.5})
    total_fwd_packets: int = Field(..., ge=0, json_schema_extra={"example": 52})
    total_bwd_packets: int = Field(..., ge=0, json_schema_extra={"example": 3})
    packet_length_mean: float = Field(..., ge=0, json_schema_extra={"example": 820.0})
    syn_flag_count: int = Field(..., ge=0, json_schema_extra={"example": 7})
    rst_flag_count: int = Field(..., ge=0, json_schema_extra={"example": 3})
    flow_bytes_per_sec: float = Field(..., ge=0, json_schema_extra={"example": 74000.0})
    failed_login_attempts: int = Field(..., ge=0, json_schema_extra={"example": 4})
    dst_port_entropy: float = Field(..., ge=0, le=1.0, json_schema_extra={"example": 0.82})

def compute_shap_values(classifier, X_trans: np.ndarray) -> np.ndarray:
    """Universal SHAP attribution extractor supporting XGBoost, Tree models, and Linear models."""
    if hasattr(classifier, "get_booster"):
        dmat = xgb.DMatrix(X_trans)
        # Native XGBoost C++ TreeSHAP computation (last column is bias offset)
        return classifier.get_booster().predict(dmat, pred_contribs=True)[0][:-1]
    elif hasattr(classifier, "coef_"):
        return (classifier.coef_[0] * X_trans[0]).astype(float)
    else:
        explainer = shap.TreeExplainer(classifier)
        sv = explainer.shap_values(X_trans)
        if isinstance(sv, list):
            return np.asarray(sv[1][0], dtype=float)
        elif len(sv.shape) == 3:
            return np.asarray(sv[0, :, 1], dtype=float)
        return np.asarray(sv[0], dtype=float)

def load_artifacts():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(META_PATH):
        raise HTTPException(status_code=503, detail="Model artifacts not found. Run training first.")
    pipeline = joblib.load(MODEL_PATH)
    with open(META_PATH, "r") as f:
        meta = json.load(f)
    return pipeline, meta

@app.get("/health")
def health_check():
    model_ready = os.path.exists(MODEL_PATH)
    return {"status": "healthy", "model_loaded": model_ready}

@app.get("/metrics")
def get_model_metrics():
    _, meta = load_artifacts()
    return meta

@app.post("/predict")
def predict_flow(flow: NetworkFlowInput):
    pipeline, meta = load_artifacts()
    df_in = pd.DataFrame([flow.model_dump()])[FEATURES]

    prob = float(pipeline.predict_proba(df_in)[0, 1])
    threshold = float(meta["optimal_threshold"])
    is_intrusion = bool(prob >= threshold)

    preprocessor = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]
    X_trans = preprocessor.transform(df_in)

    vals = compute_shap_values(classifier, X_trans)
    contributions = {feat: round(float(val), 4) for feat, val in zip(FEATURES, vals)}
    top_drivers = dict(sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:4])

    return {
        "prediction": "INTRUSION_DETECTED" if is_intrusion else "BENIGN_TRAFFIC",
        "malicious_probability": round(prob, 4),
        "decision_threshold": threshold,
        "winning_model": meta["winning_model"],
        "top_shap_drivers": top_drivers,
    }

@app.get("/drift-status")
def check_drift(use_drifted_batch: bool = True):
    ref_path = "data/raw/network_flows_reference.csv"
    cur_path = "data/raw/network_flows_drifted.csv" if use_drifted_batch else ref_path
    if not os.path.exists(ref_path) or not os.path.exists(cur_path):
        raise HTTPException(status_code=404, detail="Dataset files missing.")
    ref_df = pd.read_csv(ref_path)
    cur_df = pd.read_csv(cur_path)
    return evaluate_data_drift(ref_df, cur_df)