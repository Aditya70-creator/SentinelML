import os
import numpy as np
import pandas as pd

FEATURES = [
    "flow_duration_ms",
    "total_fwd_packets",
    "total_bwd_packets",
    "packet_length_mean",
    "syn_flag_count",
    "rst_flag_count",
    "flow_bytes_per_sec",
    "failed_login_attempts",
    "dst_port_entropy",
]

def generate_network_flows(n_samples: int = 6000, drift: bool = False, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_attack = int(n_samples * (0.22 if drift else 0.12))
    n_normal = n_samples - n_attack
    shift = 1.45 if drift else 1.0

    normal = pd.DataFrame({
        "flow_duration_ms": rng.exponential(550, n_normal) * shift,
        "total_fwd_packets": rng.poisson(18, n_normal),
        "total_bwd_packets": rng.poisson(14, n_normal),
        "packet_length_mean": rng.normal(380, 140, n_normal).clip(40, 1500) * shift,
        "syn_flag_count": rng.binomial(5, 0.22, n_normal),
        "rst_flag_count": rng.binomial(3, 0.15, n_normal),
        "flow_bytes_per_sec": rng.normal(24000, 12000, n_normal).clip(500, 180000) * shift,
        "failed_login_attempts": rng.poisson(0.35, n_normal),
        "dst_port_entropy": rng.uniform(0.10, 0.65, n_normal),
        "label": 0,
    })

    # Non-linear mix of Volumetric DDoS + Stealth Port/Brute-Force Intrusion
    stealth_mask = rng.random(n_attack) < 0.35
    attack = pd.DataFrame({
        "flow_duration_ms": np.where(stealth_mask, rng.exponential(420, n_attack), rng.exponential(1150, n_attack)) * shift,
        "total_fwd_packets": np.where(stealth_mask, rng.poisson(16, n_attack), rng.poisson(45, n_attack)),
        "total_bwd_packets": np.where(stealth_mask, rng.poisson(12, n_attack), rng.poisson(4, n_attack)),
        "packet_length_mean": np.where(stealth_mask, rng.normal(310, 90, n_attack), rng.normal(760, 190, n_attack)).clip(60, 1500) * shift,
        "syn_flag_count": np.where(stealth_mask, rng.poisson(4, n_attack), rng.poisson(6, n_attack)),
        "rst_flag_count": rng.poisson(2.5, n_attack),
        "flow_bytes_per_sec": np.where(stealth_mask, rng.normal(19000, 6000, n_attack), rng.normal(66000, 19000, n_attack)).clip(1000, 300000) * shift,
        "failed_login_attempts": np.where(stealth_mask, rng.poisson(3.5, n_attack), rng.poisson(1.8, n_attack)),
        "dst_port_entropy": np.where(stealth_mask, rng.uniform(0.68, 0.96, n_attack), rng.uniform(0.45, 0.92, n_attack)),
        "label": 1,
    })

    df = pd.concat([normal, attack], ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    # 1.5% label noise + 1% missing values to simulate real-world telemetry
    flip_mask = rng.random(len(df)) < 0.015
    df.loc[flip_mask, "label"] = 1 - df.loc[flip_mask, "label"]

    na_mask = rng.random(df[FEATURES].shape) < 0.01
    df[FEATURES] = df[FEATURES].mask(na_mask)
    return df

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    ref_df = generate_network_flows(n_samples=6000, drift=False, seed=42)
    drift_df = generate_network_flows(n_samples=1500, drift=True, seed=99)

    ref_df.to_csv("data/raw/network_flows_reference.csv", index=False)
    drift_df.to_csv("data/raw/network_flows_drifted.csv", index=False)
    print(f"[OK] Saved reference dataset ({len(ref_df)} rows) & drifted dataset ({len(drift_df)} rows).")