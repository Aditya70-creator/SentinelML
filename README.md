# 🛡️ SentinelML — Intrusion Detection & Explainable MLOps Pipeline

![Status](https://img.shields.io/badge/Status-Active_Development-10B981?style=for-the-badge)
![Domain](https://img.shields.io/badge/Domain-Cybersecurity_%26_MLOps-00E7FF?style=for-the-badge)
![Stack](https://img.shields.io/badge/Stack-XGBoost_|_SHAP_|_FastAPI_|_MLflow-8B5CF6?style=for-the-badge)

> **SentinelML** is an end-to-end supervised Machine Learning and MLOps system designed to detect network intrusions and malicious traffic patterns under severe class imbalance, complete with real-time **SHAP explainability** and **automated data-drift monitoring**.

---

## 🏗️ System Architecture

```mermaid
flowchart LR
    A(["Network Traffic<br/>Logs / Packets"]) --> B["Data Quality Gate<br/>& Feature Engineering"]
    B --> C["Imbalance Handler<br/>& Cost-Sensitive XGBoost"]
    C --> D["SHAP Explainability<br/>(Local & Global XAI)"]
    C --> E["FastAPI Inference<br/>REST Service"]
    E --> F["Drift Monitor<br/>(PSI / KS-Test & Retraining)"]

    style A fill:#070b14,stroke:#00E7FF,stroke-width:2px,color:#fff
    style B fill:#0f172a,stroke:#3B82F6,stroke-width:2px,color:#fff
    style C fill:#0f172a,stroke:#00E7FF,stroke-width:2px,color:#fff
    style D fill:#0f172a,stroke:#8B5CF6,stroke-width:2px,color:#fff
    style E fill:#0f172a,stroke:#10B981,stroke-width:2px,color:#fff
    style F fill:#070b14,stroke:#f59e0b,stroke-width:2px,color:#fff
```
