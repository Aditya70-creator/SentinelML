from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_predict_intrusion_flow():
    payload = {
        "flow_duration_ms": 1500.0,
        "total_fwd_packets": 55,
        "total_bwd_packets": 2,
        "packet_length_mean": 850.0,
        "syn_flag_count": 8,
        "rst_flag_count": 4,
        "flow_bytes_per_sec": 82000.0,
        "failed_login_attempts": 5,
        "dst_port_entropy": 0.88
    }
    res = client.post("/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"] == "INTRUSION_DETECTED"
    assert "top_shap_drivers" in data

def test_predict_benign_flow():
    payload = {
        "flow_duration_ms": 300.0,
        "total_fwd_packets": 12,
        "total_bwd_packets": 11,
        "packet_length_mean": 290.0,
        "syn_flag_count": 0,
        "rst_flag_count": 0,
        "flow_bytes_per_sec": 15000.0,
        "failed_login_attempts": 0,
        "dst_port_entropy": 0.18
    }
    res = client.post("/predict", json=payload)
    assert res.status_code == 200
    assert res.json()["prediction"] == "BENIGN_TRAFFIC"