# ADR-005: ML-Based Detection
* **Status**: Accepted
* **Context**: Traditional thresholds produce high alert fatigue. We need dynamic baseline modeling.
* **Decision**: Implement statistical models (z-score) as fallbacks and Isolation Forest/LSTM for ML anomalies.
* **Consequences**: Reduces false positives, but adds compute requirements.