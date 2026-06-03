import os
import sys
import subprocess
import time
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from hecate_db import get_db_connection

def main():
    os.environ["HECATE_DB_ENGINE"] = "sqlite"
    os.environ["HECATE_EVENT_ENGINE"] = "sqlite"
    print("[E2E Test] Starting end-to-end self-healing pipeline verification...")
    
    # 1. Clean previous database states to start fresh
    db_paths = [
        os.path.join(ROOT_DIR, "hecate_db.sqlite"),
        os.path.join(ROOT_DIR, "hecate_events.db"),
        os.path.join(ROOT_DIR, "simulation_trigger.json")
    ]
    for db in db_paths:
        if os.path.exists(db):
            try:
                os.remove(db)
            except Exception as e:
                print(f"[E2E Test] Warning: could not clear {db}: {e}")

    # Initialize the database schemas
    conn, _ = get_db_connection()
    conn.close()

    processes = []
    
    os.makedirs(os.path.join(ROOT_DIR, "tests", "logs"), exist_ok=True)

    # 2. Launch FastAPI Microservices
    services = [
        {"name": "dashboard-api", "path": "services/dashboard-api", "port": 8000},
        {"name": "anomaly-service", "path": "services/anomaly-service", "port": 8001},
        {"name": "policy-service", "path": "services/policy-service", "port": 8002}
    ]
    
    for svc in services:
        log_file = open(os.path.join(ROOT_DIR, "tests", "logs", f"{svc['name']}.log"), "w")
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.main:app", "--port", str(svc["port"])],
            cwd=os.path.join(ROOT_DIR, svc["path"]),
            stdout=log_file,
            stderr=log_file
        )
        processes.append(p)
        
    time.sleep(2)  # Wait for services to bind
    
    # 3. Launch Operational Agents
    agents = [
        {"name": "monitoring-agent", "path": "agents/monitoring-agent"},
        {"name": "detection-agent", "path": "agents/detection-agent"},
        {"name": "decision-agent", "path": "agents/decision-agent"},
        {"name": "remediation-agent", "path": "agents/remediation-agent"}
    ]
    
    for ag in agents:
        log_file = open(os.path.join(ROOT_DIR, "tests", "logs", f"{ag['name']}.log"), "w")
        p = subprocess.Popen(
            [sys.executable, "-m", "src.main"],
            cwd=os.path.join(ROOT_DIR, ag["path"]),
            stdout=log_file,
            stderr=log_file
        )
        processes.append(p)
        
    time.sleep(2)  # Wait for agent subscription loops to start
    
    try:
        # 4. Inject Crash Scenario (Scenario 1: Restart Count > 5)
        print("[E2E Test] Injecting container OOM crash simulation (Restart Count = 6)...")
        trigger_payload = {"cpu_usage": 45.0, "memory_usage": 60.0, "restart_count": 6}
        with open(os.path.join(ROOT_DIR, "simulation_trigger.json"), "w") as f:
            json.dump(trigger_payload, f)
            
        # 5. Wait for loop execution
        print("[E2E Test] Waiting 10 seconds for self-healing loop execution...")
        time.sleep(10)
        
        # 6. Verify Database Incidents and Remediations state
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        
        # Check incidents
        cursor.execute("SELECT * FROM incidents")
        incidents = [dict(row) for row in cursor.fetchall()]
        
        # Check remediations
        cursor.execute("SELECT * FROM remediations")
        remediations = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        print(f"[E2E Test] Found {len(incidents)} incident(s) and {len(remediations)} remediation run(s) in DB.")
        
        # Assertions
        assert len(incidents) > 0, "No incident was created in database!"
        assert len(remediations) > 0, "No remediation action was executed!"
        
        incident = incidents[0]
        remediation = remediations[0]
        
        print(f"[E2E Test] Incident Title: '{incident['title']}' | Status: '{incident['status']}'")
        print(f"[E2E Test] Remediation Action: '{remediation['action_type']}' | Success: {bool(remediation['success'])}")
        
        assert incident["status"] == "remediated", f"Expected incident status 'remediated', got '{incident['status']}'"
        assert remediation["action_type"] == "restart_pod", f"Expected remediation action 'restart_pod', got '{remediation['action_type']}'"
        assert bool(remediation["success"]) is True, "Remediation execution reported failure!"
        
        print("[E2E Test] SUCCESS: End-to-end self-healing pipeline verified successfully!")
        sys.exit(0)
        
    except AssertionError as ae:
        print(f"[E2E Test] FAILURE: {ae}")
        sys.exit(1)
    except Exception as ex:
        print(f"[E2E Test] ERROR: Unexpected exception: {ex}")
        sys.exit(1)
    finally:
        # Cleanup processes
        print("[E2E Test] Stopping processes...")
        for p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        # Clear simulation trigger
        sim_file = os.path.join(ROOT_DIR, "simulation_trigger.json")
        if os.path.exists(sim_file):
            os.remove(sim_file)
            
if __name__ == "__main__":
    main()
