# HECATE Platform Evaluation Summary Report

Generated on: Immutable evaluation logs

---

## Executive Summary

This report compiles functional accuracy, SRE reliability indicators, operational overhead, and reinforcement learning parameters from HECATE's automated synthetic experiment harness.

| Key Performance Indicator | Value |
| :--- | :--- |
| Anomaly Detection Precision | 100.00 % (95% CI: [100.00, 100.00]) |
| Anomaly Detection Recall | 94.00 % (95% CI: [87.42, 100.00]) |
| Root Cause Analysis Diagnosis Accuracy | 100.00 % (95% CI: [100.00, 100.00]) |
| Declarative Policy Compliance Rate | 100.00 % |
| Twin MTTR Prediction Error (MAE) | 1.71 seconds |
| Chaos Recovery Success Rate | 88.00 % (95% CI: [78.99, 97.01]) |
| Platform Availability | 99.97 % |

---

## 1. Functional & Intelligence Evaluation

### Detection & RAG Metrics
- **F1 Score**: 96.91 % (95% CI: [92.11, 100.00])
- **Early Warning Lead Time**: 33.68 seconds
- **Copilot RAG Context Recall**: 94.00 %
- **Copilot Groundedness**: 88.00 %

### Digital Twin & Learning
- **Twin Simulation RMSE**: 2.15 seconds
- **Twin Confidence Calibration Gap**: 3.99 %
- **TD-Learning Reward Convergence Delta**: 0.76 units

---

## 2. Operational Overhead

- **Latency p50 / p95**: 42.87 ms / 49.31 ms
- **Event / Simulation Throughput**: 450.00 events/sec / 12.00 simulations/sec
- **Resource Usage (Avg CPU / Peak RAM)**: 9.53 % / 59.46 MB

---

## 3. Baseline & Ablation Comparisons

### Baseline Control Groups

| Baseline Group | MTTR (sec) | Recovery Success (%) | Availability (%) |
| :--- | :---: | :---: | :---: |
| Baseline 0 (No Remediation) | 300.30s | 0.00% | 90.0375% |
| Baseline 1 (Threshold Rules) | 45.94s | 69.02% | 98.1349% |
| Baseline 2 (Random Playbook) | 55.13s | 24.84% | 96.4992% |
| Baseline 3 (Historical Recs) | 21.15s | 84.44% | 99.1389% |
| Baseline 4 (Prediction Only) | 19.57s | 87.06% | 99.2234% |
| Baseline 5 (Pred + Rec) | 14.34s | 91.18% | 99.3521% |
| Baseline 6 (Full HECATE) | 12.38s | 96.48% | 99.5908% |

### Subsystem Ablation Study

| Disabled Subsystem | MTTR (sec) | Diagnosis Precision (%) | Availability (%) |
| :--- | :---: | :---: | :---: |
| Full HECATE Pipeline | 11.65s | 95.28% | 99.6375% |
| Without Prediction | 15.47s | 91.02% | 99.3349% |
| Without Twin | 18.56s | 95.64% | 99.1992% |
| Without Learning | 13.07s | 96.24% | 99.5389% |
| Without Graph | 16.03s | 83.06% | 99.3234% |
| Without Copilot | 11.57s | 95.98% | 99.5521% |
| Without HITL Governance | 11.44s | 95.78% | 99.0908% |

---

## 4. Statistical Significance Tests

To determine the scientific validity of HECATE's MTTR reduction compared to static rules, we run hypothesis tests:

- **Welch's t-test**:
  - $t$-statistic: `52.7904`
  - $p$-value: `0.0000e+00` (Statistically significant if $p < 0.05$)
- **Mann-Whitney U Test**:
  - $U$-statistic: `0.00`
  - $p$-value: `0.0000e+00`
- **Cohen's d Effect Size**: `10.8898` (Values > 0.8 represent large effects)
- **Bootstrap 95% CI on HECATE MTTR**: `[29.77, 30.68]` seconds.
