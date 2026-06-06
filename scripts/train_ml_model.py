import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

def main():
    print("[ML Train] Generating synthetic training dataset...")
    np.random.seed(42)
    
    # 1. Generate normal baseline data (1000 samples)
    # CPU: 20-50%, Memory: 40-70%, Restart Count: 0
    normal_cpu = np.random.uniform(20.0, 50.0, 1000)
    normal_mem = np.random.uniform(40.0, 70.0, 1000)
    normal_restarts = np.zeros(1000)
    normal_data = np.column_stack((normal_cpu, normal_mem, normal_restarts))
    
    # 2. Generate anomalous outlier data (100 samples)
    anom_cpu = np.concatenate([
        np.random.uniform(88.0, 100.0, 40), # CPU spikes
        np.random.uniform(20.0, 50.0, 60)
    ])
    anom_mem = np.concatenate([
        np.random.uniform(40.0, 70.0, 40),
        np.random.uniform(85.0, 100.0, 40), # Mem spikes
        np.random.uniform(40.0, 70.0, 20)
    ])
    anom_restarts = np.concatenate([
        np.zeros(80),
        np.random.uniform(6.0, 10.0, 20) # Restarts spikes
    ])
    anom_data = np.column_stack((anom_cpu, anom_mem, anom_restarts))
    
    # Combine dataset
    X_train = np.vstack((normal_data, anom_data))
    print(f"[ML Train] Total training samples: {X_train.shape[0]} ({normal_data.shape[0]} normal, {anom_data.shape[0]} anomalies)")
    
    # 3. Train Isolation Forest
    print("[ML Train] Fitting Isolation Forest model...")
    # contamination=0.10 means we expect ~10% anomalies in the combined dataset
    model = IsolationForest(n_estimators=100, contamination=0.10, random_state=42)
    model.fit(X_train)
    
    # Verify model works
    print("[ML Train] Testing model predictions...")
    test_normal = np.array([[35.0, 55.0, 0.0]]) # Should be 1 (normal)
    test_anom_cpu = np.array([[95.0, 55.0, 0.0]]) # Should be -1 (anomaly)
    test_anom_rest = np.array([[30.0, 50.0, 7.0]]) # Should be -1 (anomaly)
    
    pred_normal = model.predict(test_normal)[0]
    pred_anom_cpu = model.predict(test_anom_cpu)[0]
    pred_anom_rest = model.predict(test_anom_rest)[0]
    
    print(f"  Normal sample [35, 55, 0] predicted: {pred_normal} (Expected: 1)")
    print(f"  CPU spike sample [95, 55, 0] predicted: {pred_anom_cpu} (Expected: -1)")
    print(f"  Restarts sample [30, 50, 7] predicted: {pred_anom_rest} (Expected: -1)")
    
    # 4. Save model artifact
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml", "models"))
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, "isolation_forest.pkl")
    
    print(f"[ML Train] Saving model binary to {model_path}...")
    joblib.dump(model, model_path)
    print("[ML Train] Training complete!")

if __name__ == "__main__":
    main()
