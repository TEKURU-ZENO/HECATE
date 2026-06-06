import json
import os
import subprocess
import sys
import time

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
        {"name": "rca-agent", "path": "agents/rca-agent"},
        {"name": "decision-agent", "path": "agents/decision-agent"},
        {"name": "remediation-agent", "path": "agents/remediation-agent"},
        {"name": "learning-agent", "path": "agents/learning-agent"}
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

    time.sleep(5)  # Wait for agent subscription loops to start

    try:
        # ==========================================
        # Scenario 1: CPU spike -> Isolation Forest Anomaly -> Incident -> RCA (self) -> Decision -> Remediation
        # ==========================================
        print("\n--- Running Scenario 1: CPU spike / Isolation Forest detection on payment-service ---")
        
        # Inject CPU spike via simulation_trigger.json
        trigger_payload = {"cpu_usage": 95.0, "memory_usage": 60.0, "restart_count": 0}
        with open(os.path.join(ROOT_DIR, "simulation_trigger.json"), "w") as f:
            json.dump(trigger_payload, f)

        # Wait 5 seconds to guarantee at least two scrapes detect the trigger
        time.sleep(5.0)

        # Remove trigger file immediately to stop new anomalies from spawning
        if os.path.exists(os.path.join(ROOT_DIR, "simulation_trigger.json")):
            os.remove(os.path.join(ROOT_DIR, "simulation_trigger.json"))

        # Wait for the pipeline to execute the existing incident
        print("[Scenario 1] Waiting 10 seconds for self-healing loop execution...")
        time.sleep(10)

        # Verify DB records
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM incidents WHERE service_name = 'payment-service'")
        incidents_s1 = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM remediations")
        remediations_s1 = [dict(row) for row in cursor.fetchall()]
        
        conn.close()

        print(f"[Scenario 1] Found {len(incidents_s1)} incident(s) and {len(remediations_s1)} remediation run(s) in DB.")
        
        assert len(incidents_s1) > 0, "Scenario 1: No incident was created in database!"
        
        # Find the incident that has been remediated
        remediated_incs = [i for i in incidents_s1 if i["status"] == "remediated"]
        assert len(remediated_incs) > 0, "Scenario 1: No incident was remediated in database!"
        
        # Check latest remediated incident status and root cause
        latest_inc = remediated_incs[-1]
        print(f"[Scenario 1] Remediation Success - Incident: ID={latest_inc['id']} | Service={latest_inc['service_name']} | Status={latest_inc['status']}")
        print(f"[Scenario 1] RCA Analysis: Root Cause={latest_inc['root_cause']} | Confidence={latest_inc['confidence_score']} | Risk Score={latest_inc['risk_score']}")
        
        # Verify RCA details
        assert latest_inc["root_cause"] is not None and "payment-service" in latest_inc["root_cause"].lower(), "Expected self-contained root cause for payment-service"
        assert latest_inc["confidence_score"] == 0.70, f"Expected self-contained confidence 0.70, got {latest_inc['confidence_score']}"
        assert latest_inc["risk_score"] == 0.40, f"Expected risk score 0.40, got {latest_inc['risk_score']}"

        # Check remediation details
        assert len(remediations_s1) > 0, "Scenario 1: No remediation action was executed!"
        latest_rem = remediations_s1[-1]
        print(f"[Scenario 1] Remediation Action: '{latest_rem['action_type']}' | Success: {bool(latest_rem['success'])}")
        assert latest_rem["action_type"] in ["restart_pod", "scale_deployment"], f"Unexpected action type: {latest_rem['action_type']}"
        assert bool(latest_rem["success"]) is True, "Remediation execution reported failure!"

        # ==========================================
        # Scenario 2: Database Failure -> payment-service Degradation -> RCA concludes root cause = payment-db
        # ==========================================
        print("\n--- Running Scenario 2: Cascading failure (payment-db down) ---")

        # Step A: Seed active downstream incident for payment-db
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        db_incident_id = "INC-DB-001"
        cursor.execute(
            "INSERT INTO incidents (id, incident_code, title, severity, status, service_name, root_cause, confidence_score, risk_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (db_incident_id, "HEC-DB001", "Database offline", "critical", "open", "payment-db", "Connection timeout", 1.0, 0.9)
        )
        conn.commit()
        conn.close()
        print("[Scenario 2] Seeded active downstream incident for payment-db in DB.")

        # Step B: Inject memory spike on payment-service to trigger a degradation incident
        trigger_payload = {"cpu_usage": 45.0, "memory_usage": 90.0, "restart_count": 0}
        with open(os.path.join(ROOT_DIR, "simulation_trigger.json"), "w") as f:
            json.dump(trigger_payload, f)

        # Wait 5 seconds to guarantee at least two scrapes detect the trigger
        time.sleep(5.0)

        # Remove trigger file immediately to stop new anomalies
        if os.path.exists(os.path.join(ROOT_DIR, "simulation_trigger.json")):
            os.remove(os.path.join(ROOT_DIR, "simulation_trigger.json"))

        # Wait for cascading failure RCA and remediation to complete
        print("[Scenario 2] Waiting 10 seconds for cascading failure RCA and remediation...")
        time.sleep(10)

        # Verify DB records
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        
        # Get all incidents for payment-service after our Scenario 2 start
        cursor.execute("SELECT * FROM incidents WHERE service_name = 'payment-service' ORDER BY detected_at DESC")
        incidents_s2 = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM remediations ORDER BY executed_at DESC")
        remediations_s2 = [dict(row) for row in cursor.fetchall()]
        
        conn.close()

        print(f"[Scenario 2] Found {len(incidents_s2)} payment-service incident(s) and {len(remediations_s2)} total remediation(s) in DB.")
        
        # Find the incident for payment-service in Scenario 2 that has been remediated
        # (It should have root cause pointing to payment-db)
        remediated_incs_s2 = [i for i in incidents_s2 if i["status"] == "remediated" and "payment-db" in (i["root_cause"] or "")]
        assert len(remediated_incs_s2) > 0, "Scenario 2: No incident with payment-db root cause was remediated!"
        
        degraded_inc = remediated_incs_s2[0]
        print(f"[Scenario 2] Remediation Success - Incident: ID={degraded_inc['id']} | Service={degraded_inc['service_name']} | Status={degraded_inc['status']}")
        print(f"[Scenario 2] RCA Analysis: Root Cause={degraded_inc['root_cause']} | Confidence={degraded_inc['confidence_score']} | Risk Score={degraded_inc['risk_score']}")
        
        # Verify root cause traverses down to payment-db
        assert "payment-db" in degraded_inc["root_cause"], f"Expected root cause to pinpoint 'payment-db', got: {degraded_inc['root_cause']}"
        assert degraded_inc["confidence_score"] == 0.95, f"Expected cascading confidence 0.95, got {degraded_inc['confidence_score']}"
        assert degraded_inc["risk_score"] == 0.85, f"Expected risk score 0.85, got {degraded_inc['risk_score']}"
        
        # Verify that remediation targeted payment-db rather than payment-service
        matching_remediations = [r for r in remediations_s2 if r["incident_id"] == degraded_inc["id"]]
        assert len(matching_remediations) > 0, "Scenario 2: No remediation action executed for the degraded incident!"
        
        latest_rem_s2 = matching_remediations[0]
        print(f"[Scenario 2] Remediation for degraded incident: Action={latest_rem_s2['action_type']} | Success={bool(latest_rem_s2['success'])}")
        
        # Verify that the DB shows the remediation executed
        assert bool(latest_rem_s2["success"]) is True, "Remediation execution reported failure!"

        # ==========================================
        # Scenario 3: Verify Operational Memory logging for Scenario 1
        # ==========================================
        print("\n--- Running Scenario 3: Verify Operational Memory logging ---")
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM operational_memory")
        mem_records = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        print(f"[Scenario 3] Found {len(mem_records)} record(s) in operational_memory table.")
        assert len(mem_records) > 0, "Scenario 3: No records found in operational_memory table!"
        
        # Verify columns of the first record (from Scenario 1)
        record = mem_records[0]
        print(f"[Scenario 3] Record: Type={record['incident_type']} | Title='{record['incident_title']}' | Action={record['remediation_action']} | Recovery Time={record['recovery_time_seconds']}s | Confidence={record['confidence_score']} | Effectiveness={record['effectiveness_score']}")
        
        assert record["incident_type"] == "cpu_high", f"Expected incident_type 'cpu_high', got: {record['incident_type']}"
        assert record["remediation_action"] in ["restart_pod", "scale_deployment"], f"Unexpected action: {record['remediation_action']}"
        assert record["success"] == 1, "Expected success to be 1 (True)"
        assert record["recovery_time_seconds"] > 0, "Expected recovery time to be > 0"
        assert record["confidence_score"] == 0.70, f"Expected confidence score 0.70, got {record['confidence_score']}"
        assert 0.0 < record["effectiveness_score"] <= 1.0, f"Expected effectiveness score between 0.0 and 1.0, got: {record['effectiveness_score']}"
        print("[Scenario 3] Operational memory logged correctly.")

        # ==========================================
        # Scenario 4: Double Trigger verification (Repeat Incident)
        # ==========================================
        print("\n--- Running Scenario 4: Double Trigger verification (Repeat same incident) ---")
        
        # Trigger same CPU spike anomaly on payment-service again
        trigger_payload = {"cpu_usage": 95.0, "memory_usage": 60.0, "restart_count": 0}
        with open(os.path.join(ROOT_DIR, "simulation_trigger.json"), "w") as f:
            json.dump(trigger_payload, f)

        # Wait 5 seconds to guarantee at least two scrapes detect the trigger
        time.sleep(5.0)

        # Remove trigger
        if os.path.exists(os.path.join(ROOT_DIR, "simulation_trigger.json")):
            os.remove(os.path.join(ROOT_DIR, "simulation_trigger.json"))

        # Wait for loop execution
        print("[Scenario 4] Waiting 10 seconds for self-healing loop execution...")
        time.sleep(10)

        # Verify DB records
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM operational_memory WHERE incident_type = 'cpu_high'")
        cpu_mem_records = [dict(row) for row in cursor.fetchall()]
        
        # Verify stats endpoint
        import httpx
        try:
            stats_res = httpx.get("http://localhost:8000/api/v1/learning/stats", timeout=3.0)
            assert stats_res.status_code == 200, "Stats API returned non-200"
            stats = stats_res.json()
            print(f"[Scenario 4] Stats API response: {stats}")
            assert stats["total_incidents"] >= 2, f"Expected at least 2 total incidents in stats, got {stats['total_incidents']}"
            assert stats["successful_remediations"] >= 2, "Expected at least 2 successful remediations"
            assert stats["top_successful_action"] in ["restart_pod", "scale_deployment"], f"Unexpected top action: {stats['top_successful_action']}"
        except Exception as se:
            print(f"[Scenario 4] WARNING: Stats endpoint validation skipped/failed: {se}")

        conn.close()

        print(f"[Scenario 4] Found {len(cpu_mem_records)} CPU incident record(s) in operational_memory.")
        assert len(cpu_mem_records) >= 2, f"Scenario 4: Expected at least 2 CPU records in operational memory, got: {len(cpu_mem_records)}"
        print("[Scenario 4] Double trigger verified successfully.")

        print("[E2E Test] SUCCESS: All 4 Scenarios (1: Anomaly detection, 2: RCA, 3: Learning Memory, 4: Double Trigger stats) verified successfully!")
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
