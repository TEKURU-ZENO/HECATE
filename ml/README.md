# HECATE ML Module

> **Autonomous anomaly detection powered by machine learning** — trained on infrastructure metrics, served via a low-latency inference API.

---

## Module Overview

The `ml/` module provides the machine learning backbone for HECATE's detection-agent. Rather than relying solely on static thresholds, HECATE uses trained models to detect subtle, multi-dimensional anomalies in infrastructure metrics streams.

---

## Model Inventory

| Model Name | Algorithm | Purpose | Status | Session |
|-----------|-----------|---------|--------|---------|
| `IsolationForestDetector` | Isolation Forest | Unsupervised anomaly detection on tabular metrics | 🔲 Stub | Session 3 |
| `LSTMDetector` | LSTM Autoencoder | Temporal anomaly detection on time-series sequences | 🔲 Stub | Session 3 |
| `AutoencoderDetector` | Deep Autoencoder | Reconstruction-error-based anomaly detection | 🔲 Stub | Session 3 |
| `EnsembleDetector` | Voting Ensemble | Combines all three models with weighted voting | 🔲 Stub | Session 3 |

**Status key:** 🔲 Stub | 🔧 In Progress | ✅ Implemented | 🧪 Tested | 🚀 Deployed

---

## Input Features

All models consume the same feature vector (sampled every 15 seconds):

| Feature | Source | Unit |
|---------|--------|------|
| `cpu_usage_pct` | cAdvisor / Prometheus | % (0–1) |
| `memory_usage_pct` | cAdvisor / Prometheus | % (0–1) |
| `network_rx_bytes_rate` | Node Exporter | bytes/s |
| `network_tx_bytes_rate` | Node Exporter | bytes/s |
| `error_rate_5xx` | Service metrics | ratio (0–1) |
| `request_latency_p99` | Service metrics | seconds |
| `kafka_consumer_lag` | Kafka JMX | message count |
| `pod_restart_count` | kube-state-metrics | count |

---

## Training Pipeline Overview

```
Raw Prometheus Metrics
        │
        ▼
  Feature Engineering
  (windowing, normalization, lag features)
        │
        ▼
  Training Script (train_isolation_forest.py)
        │
        ├──► Model artifact (.pkl / .pt)
        ├──► Scaler artifact (.pkl)
        └──► Evaluation metrics (precision, recall, F1)
```

Training scripts are located in `training/`. Each script:
1. Loads data from `datasets/`
2. Runs cross-validation
3. Outputs model artifacts to `models/<model_name>/artifacts/`
4. Logs metrics to MLflow (future)

---

## Inference Serving Architecture

```
detection-agent (Kafka consumer)
        │
        │  raw metrics message
        ▼
 Inference Server (FastAPI)
  - POST /predict
  - GET  /health
  - GET  /models
        │
        │  anomaly_score, is_anomaly, explanation
        ▼
 detection-agent → publishes to anomaly.detected topic
```

The inference server (`inference/server.py`) loads all model artifacts at startup and serves predictions via a unified REST API. The detection-agent calls it synchronously for each metrics window.

---

## MLOps Practices

- **Versioning**: All model artifacts are versioned with `<model>_v<semver>_<timestamp>.pkl`
- **A/B Testing**: The inference server supports shadow mode for comparing new models (Session 3+)
- **Drift Detection**: Statistical drift detection on input feature distributions (Session 3+)
- **Retraining Triggers**: Scheduled weekly retraining + manual trigger via API (Session 3+)
- **Experiment Tracking**: MLflow for metrics, parameters, and artifacts (Session 3+)

---

## Quick Start (Session 3)

```bash
# Install ML dependencies
pip install -r ml/requirements.txt

# Generate synthetic training data
python ml/datasets/generate_synthetic_data.py --samples 50000 --anomaly-rate 0.05

# Train the Isolation Forest model
python ml/training/train_isolation_forest.py \
  --data ml/datasets/synthetic_metrics.parquet \
  --output ml/models/isolation_forest/artifacts/

# Start the inference server
uvicorn ml.inference.server:app --host 0.0.0.0 --port 8001 --reload

# Test inference
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"cpu_usage_pct": 0.97, "memory_usage_pct": 0.85, "error_rate_5xx": 0.12}'
```
