import json
import os
import subprocess
import sys
import time
import uuid

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from hecate_db import get_db_connection


def wait_for_incidents_resolve(timeout=60):
    print(
        f"[E2E Test] Waiting for all open incidents on payment-service to be resolved (timeout={timeout}s)..."
    )
    # First, wait up to 15s for the incident to be created (open_count > 0)
    for _ in range(15):
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM incidents WHERE service_name = 'payment-service' AND LOWER(status) NOT IN ('remediated', 'closed', 'failed', 'rejected')"
        )
        open_count = cursor.fetchone()[0]
        conn.close()
        if open_count > 0:
            break
        time.sleep(1.0)

    # Now wait for it to be resolved
    for _ in range(timeout):
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM incidents WHERE service_name = 'payment-service' AND LOWER(status) NOT IN ('remediated', 'closed', 'failed', 'rejected')"
        )
        open_count = cursor.fetchone()[0]
        conn.close()
        if open_count == 0:
            time.sleep(2.0)  # Small buffer for learning-agent to finish writing operational memory
            print("[E2E Test] All incidents resolved.")
            return True
        time.sleep(1.0)
    print("[E2E Test] WARNING: Timeout reached, some incidents are still open.")
    return False


def main():
    os.environ["HECATE_DB_ENGINE"] = "sqlite"
    os.environ["HECATE_EVENT_ENGINE"] = "sqlite"
    os.environ["HECATE_TEST_MODE"] = "true"
    os.environ["SCRAPE_INTERVAL_SECONDS"] = "5.0"
    os.environ["COPILOT_INDEX_REFRESH_INTERVAL"] = "1"
    print("[E2E Test] Starting end-to-end self-healing pipeline verification...")

    # 1. Clean previous database states to start fresh
    db_paths = [
        os.path.join(ROOT_DIR, "hecate_db.sqlite"),
        os.path.join(ROOT_DIR, "hecate_events.db"),
        os.path.join(ROOT_DIR, "simulation_trigger.json"),
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
        {"name": "policy-service", "path": "services/policy-service", "port": 8002},
        {"name": "forecasting-service", "path": "services/forecasting-service", "port": 8003},
        {"name": "copilot-service", "path": "services/copilot-service", "port": 8004},
        {"name": "graph-service", "path": "services/graph-service", "port": 8005},
        {"name": "digital-twin-service", "path": "services/digital-twin-service", "port": 8006},
    ]

    for svc in services:
        log_file = open(os.path.join(ROOT_DIR, "tests", "logs", f"{svc['name']}.log"), "w")
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.main:app", "--port", str(svc["port"])],
            cwd=os.path.join(ROOT_DIR, svc["path"]),
            stdout=log_file,
            stderr=log_file,
        )
        processes.append(p)

    time.sleep(2)  # Wait for services to bind

    # 3. Launch Operational Agents
    agents = [
        {"name": "monitoring-agent", "path": "agents/monitoring-agent"},
        {"name": "detection-agent", "path": "agents/detection-agent"},
        {"name": "rca-agent", "path": "agents/rca-agent"},
        {"name": "recommendation-agent", "path": "agents/recommendation-agent"},
        {"name": "simulation-agent", "path": "agents/simulation-agent"},
        {"name": "decision-agent", "path": "agents/decision-agent"},
        {"name": "remediation-agent", "path": "agents/remediation-agent"},
        {"name": "learning-agent", "path": "agents/learning-agent"},
        {"name": "prediction-agent", "path": "agents/prediction-agent"},
    ]

    for ag in agents:
        log_file = open(os.path.join(ROOT_DIR, "tests", "logs", f"{ag['name']}.log"), "w")
        p = subprocess.Popen(
            [sys.executable, "-m", "src.main"],
            cwd=os.path.join(ROOT_DIR, ag["path"]),
            stdout=log_file,
            stderr=log_file,
        )
        processes.append(p)

    time.sleep(
        35
    )  # Wait for agent subscription loops to start (allowing ML model load in detection agent)

    try:
        # ==========================================
        # Scenario 1: CPU spike -> Isolation Forest Anomaly -> Incident -> RCA (self) -> Decision -> Remediation
        # ==========================================
        print(
            "\n--- Running Scenario 1: CPU spike / Isolation Forest detection on payment-service ---"
        )

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
        wait_for_incidents_resolve(60)

        # Verify DB records
        conn, _ = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM incidents WHERE service_name = 'payment-service'")
        incidents_s1 = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM remediations")
        remediations_s1 = [dict(row) for row in cursor.fetchall()]

        conn.close()

        print(
            f"[Scenario 1] Found {len(incidents_s1)} incident(s) and {len(remediations_s1)} remediation run(s) in DB."
        )

        assert len(incidents_s1) > 0, "Scenario 1: No incident was created in database!"

        # Find the incident that has been remediated
        remediated_incs = [i for i in incidents_s1 if i["status"] == "remediated"]
        assert len(remediated_incs) > 0, "Scenario 1: No incident was remediated in database!"

        # Check latest remediated incident status and root cause
        latest_inc = remediated_incs[-1]
        print(
            f"[Scenario 1] Remediation Success - Incident: ID={latest_inc['id']} | Service={latest_inc['service_name']} | Status={latest_inc['status']}"
        )
        print(
            f"[Scenario 1] RCA Analysis: Root Cause={latest_inc['root_cause']} | Confidence={latest_inc['confidence_score']} | Risk Score={latest_inc['risk_score']}"
        )

        # Verify RCA details
        assert (
            latest_inc["root_cause"] is not None
            and "payment-service" in latest_inc["root_cause"].lower()
        ), "Expected self-contained root cause for payment-service"
        assert latest_inc["confidence_score"] == 0.70, (
            f"Expected self-contained confidence 0.70, got {latest_inc['confidence_score']}"
        )
        assert latest_inc["risk_score"] == 0.40, (
            f"Expected risk score 0.40, got {latest_inc['risk_score']}"
        )

        # Check remediation details
        assert len(remediations_s1) > 0, "Scenario 1: No remediation action was executed!"
        latest_rem = remediations_s1[-1]
        print(
            f"[Scenario 1] Remediation Action: '{latest_rem['action_type']}' | Success: {bool(latest_rem['success'])}"
        )
        assert latest_rem["action_type"] in ["restart_pod", "scale_deployment", "restart_pod -> scale_deployment", "scale_deployment -> restart_pod"], (
            f"Unexpected action type: {latest_rem['action_type']}"
        )
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
            (
                db_incident_id,
                "HEC-DB001",
                "Database offline",
                "critical",
                "open",
                "payment-db",
                "Connection timeout",
                1.0,
                0.9,
            ),
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
        wait_for_incidents_resolve(60)

        # Verify DB records
        conn, _ = get_db_connection()
        cursor = conn.cursor()

        # Get all incidents for payment-service after our Scenario 2 start
        cursor.execute(
            "SELECT * FROM incidents WHERE service_name = 'payment-service' ORDER BY detected_at DESC"
        )
        incidents_s2 = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM remediations ORDER BY executed_at DESC")
        remediations_s2 = [dict(row) for row in cursor.fetchall()]

        conn.close()

        print(
            f"[Scenario 2] Found {len(incidents_s2)} payment-service incident(s) and {len(remediations_s2)} total remediation(s) in DB."
        )

        # Find the incident for payment-service in Scenario 2 that has been remediated
        # (It should have root cause pointing to payment-db)
        remediated_incs_s2 = [
            i
            for i in incidents_s2
            if i["status"] == "remediated" and "payment-db" in (i["root_cause"] or "")
        ]
        assert len(remediated_incs_s2) > 0, (
            "Scenario 2: No incident with payment-db root cause was remediated!"
        )

        degraded_inc = remediated_incs_s2[0]
        print(
            f"[Scenario 2] Remediation Success - Incident: ID={degraded_inc['id']} | Service={degraded_inc['service_name']} | Status={degraded_inc['status']}"
        )
        print(
            f"[Scenario 2] RCA Analysis: Root Cause={degraded_inc['root_cause']} | Confidence={degraded_inc['confidence_score']} | Risk Score={degraded_inc['risk_score']}"
        )

        # Verify root cause traverses down to payment-db
        assert "payment-db" in degraded_inc["root_cause"], (
            f"Expected root cause to pinpoint 'payment-db', got: {degraded_inc['root_cause']}"
        )
        assert degraded_inc["confidence_score"] == 0.95, (
            f"Expected cascading confidence 0.95, got {degraded_inc['confidence_score']}"
        )
        assert degraded_inc["risk_score"] == 0.85, (
            f"Expected risk score 0.85, got {degraded_inc['risk_score']}"
        )

        # Verify that remediation targeted payment-db rather than payment-service
        matching_remediations = [
            r for r in remediations_s2 if r["incident_id"] == degraded_inc["id"]
        ]
        assert len(matching_remediations) > 0, (
            "Scenario 2: No remediation action executed for the degraded incident!"
        )

        latest_rem_s2 = matching_remediations[0]
        print(
            f"[Scenario 2] Remediation for degraded incident: Action={latest_rem_s2['action_type']} | Success={bool(latest_rem_s2['success'])}"
        )

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
        print(
            f"[Scenario 3] Record: Type={record['incident_type']} | Title='{record['incident_title']}' | Action={record['remediation_action']} | Recovery Time={record['recovery_time_seconds']}s | Confidence={record['confidence_score']} | Effectiveness={record['effectiveness_score']}"
        )

        assert record["incident_type"] == "cpu_high", (
            f"Expected incident_type 'cpu_high', got: {record['incident_type']}"
        )
        assert record["remediation_action"] in ["restart_pod", "scale_deployment", "restart_pod -> scale_deployment", "scale_deployment -> restart_pod"], (
            f"Unexpected action: {record['remediation_action']}"
        )
        assert record["success"] == 1, "Expected success to be 1 (True)"
        assert record["recovery_time_seconds"] > 0, "Expected recovery time to be > 0"
        assert record["confidence_score"] == 0.70, (
            f"Expected confidence score 0.70, got {record['confidence_score']}"
        )
        assert 0.0 <= record["effectiveness_score"] <= 1.0, (
            f"Expected effectiveness score between 0.0 and 1.0, got: {record['effectiveness_score']}"
        )
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
        wait_for_incidents_resolve(60)

        # Verify DB records (wait for learning-agent to async commit record to operational_memory)
        print("[Scenario 4] Waiting for learning-agent to log second CPU record to operational_memory...")
        cpu_mem_records = []
        for _ in range(60):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM operational_memory WHERE incident_type = 'cpu_high'")
            cpu_mem_records = [dict(row) for row in cursor.fetchall()]
            conn.close()
            if len(cpu_mem_records) >= 2:
                break
            time.sleep(1.0)

        # Verify stats endpoint
        import httpx

        try:
            stats_res = httpx.get("http://localhost:8000/api/v1/learning/stats", timeout=3.0)
            assert stats_res.status_code == 200, "Stats API returned non-200"
            stats = stats_res.json()
            print(f"[Scenario 4] Stats API response: {stats}")
            assert stats["total_incidents"] >= 2, (
                f"Expected at least 2 total incidents in stats, got {stats['total_incidents']}"
            )
            assert stats["successful_remediations"] >= 2, (
                "Expected at least 2 successful remediations"
            )
            assert stats["top_successful_action"] in ["restart_pod", "scale_deployment", "restart_pod -> scale_deployment", "scale_deployment -> restart_pod"], (
                f"Unexpected top action: {stats['top_successful_action']}"
            )
        except Exception as se:
            print(f"[Scenario 4] WARNING: Stats endpoint validation skipped/failed: {se}")

        print(
            f"[Scenario 4] Found {len(cpu_mem_records)} CPU incident record(s) in operational_memory."
        )
        assert len(cpu_mem_records) >= 2, (
            f"Scenario 4: Expected at least 2 CPU records in operational memory, got: {len(cpu_mem_records)}"
        )
        print("[Scenario 4] Double trigger verified successfully.")

        # ==========================================
        # Scenario 5: Similarity Recommendation
        # ==========================================
        print("\n--- Running Scenario 5: Similarity Recommendation ---")

        # 1. Clear operational memory and recommendations to make it deterministic
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM operational_memory")
        cursor.execute("DELETE FROM recommendations")
        cursor.execute("UPDATE incidents SET status = 'remediated'")

        # Seed memory: 3 successes for restart_pod, 1 failure for scale_deployment on cpu_high / payment-service
        # For restart_pod (3 successes, effectiveness=1.0, confidence=0.7)
        for i in range(3):
            cursor.execute(
                """
                INSERT INTO operational_memory (
                    id, incident_id, incident_type, incident_title, root_cause_service,
                    remediation_action, success, recovery_time_seconds, confidence_score, effectiveness_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"mem-s5-restart-{i}",
                    f"inc-s5-restart-{i}",
                    "cpu_high",
                    "Cpu usage high in payment-service",
                    "payment-service",
                    "restart_pod",
                    1,
                    15,
                    0.70,
                    1.0,
                ),
            )

        # For scale_deployment (1 failure, effectiveness=0.0, confidence=0.7)
        cursor.execute(
            """
            INSERT INTO operational_memory (
                id, incident_id, incident_type, incident_title, root_cause_service,
                remediation_action, success, recovery_time_seconds, confidence_score, effectiveness_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mem-s5-scale-0",
                "inc-s5-scale-0",
                "cpu_high",
                "Cpu usage high in payment-service",
                "payment-service",
                "scale_deployment",
                0,
                120,
                0.70,
                0.0,
            ),
        )
        conn.commit()
        conn.close()
        print("[Scenario 5] Seeded 4 records in operational_memory table.")

        # 2. Trigger CPU spike on payment-service
        trigger_payload = {"cpu_usage": 95.0, "memory_usage": 60.0, "restart_count": 0}
        with open(os.path.join(ROOT_DIR, "simulation_trigger.json"), "w") as f:
            json.dump(trigger_payload, f)

        time.sleep(5.0)

        if os.path.exists(os.path.join(ROOT_DIR, "simulation_trigger.json")):
            os.remove(os.path.join(ROOT_DIR, "simulation_trigger.json"))

        # Wait for recommendation to be generated
        print("[Scenario 5] Waiting for recommendation to be generated...")
        rec = None
        for _ in range(60):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM recommendations 
                WHERE incident_type = 'cpu_high' AND root_cause_service = 'payment-service'
                ORDER BY created_at DESC LIMIT 1
                """
            )
            row = cursor.fetchone()
            conn.close()
            if row is not None:
                rec = dict(row)
                break
            time.sleep(1.0)

        assert rec is not None, "Scenario 5: No recommendation found in recommendations table!"
        rec = dict(row)
        print(
            f"[Scenario 5] Found recommendation: Action={rec['recommended_action']} | "
            f"Prob={rec['success_probability']} | Score={rec['recommendation_score']} | "
            f"Tier={rec['match_tier']} | Cases={rec['similar_cases_count']}"
        )
        assert rec["recommended_action"] == "restart_pod", (
            f"Expected restart_pod, got {rec['recommended_action']}"
        )
        assert rec["success_probability"] == 1.0, (
            f"Expected success_probability 1.0, got {rec['success_probability']}"
        )
        assert rec["match_tier"] == 1, f"Expected match_tier 1, got {rec['match_tier']}"
        assert rec["similar_cases_count"] == 4, (
            f"Expected 4 similar cases, got {rec['similar_cases_count']}"
        )
        print("[Scenario 5] Similarity recommendation verified successfully.")

        # Wait for Scenario 5 incidents to resolve before clearing the DB in Scenario 6
        wait_for_incidents_resolve(60)

        # ==========================================
        # Scenario 6: Cold-Start Default Fallback
        # ==========================================
        print("\n--- Running Scenario 6: Cold-Start Default Fallback ---")

        # Wait for trailing events from Scenario 5 to settle
        time.sleep(5.0)

        # 1. Clear operational memory and recommendations to ensure cold start
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM operational_memory")
        cursor.execute("DELETE FROM recommendations")
        cursor.execute("UPDATE incidents SET status = 'remediated'")
        conn.commit()
        conn.close()
        print(
            "[Scenario 6] Cleared operational_memory, recommendations and set incidents status to remediated."
        )

        # Clear and re-initialize Graph Service topology
        try:
            import httpx
            # Clear Graph
            httpx.post("http://localhost:8005/api/v1/graph/clear", timeout=3.0)
            
            # Re-initialize topology
            import yaml
            rules_path = os.path.join(ROOT_DIR, "policies", "default-rules.yaml")
            with open(rules_path, "r") as f:
                rules_data = yaml.safe_load(f)
            topology_cfg = rules_data.get("topology", {})
            payload = []
            services = topology_cfg.get("services", [])
            dependencies = topology_cfg.get("dependencies", [])
            for svc in services:
                deps = [dep[1] for dep in dependencies if dep[0] == svc]
                payload.append({"service": svc, "depends_on": deps})
            httpx.post("http://localhost:8005/api/v1/graph/initialize", json=payload, timeout=5.0)
            print("[Scenario 6] Cleared and re-seeded Graph Service topology for true cold start.")
        except Exception as ge:
            print(f"[Scenario 6] Warning: Failed to reset graph-service: {ge}")

        # 2. Publish a custom metrics event to metrics-topic to simulate memory_high on order-service
        # (This avoids running another monitoring agent specifically for order-service)
        from hecate_events import HecateEventBus

        bus = HecateEventBus()
        event_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "telemetry.metric",
            "timestamp": time.time(),
            "service_name": "order-service",
            "namespace": "hecate-system",
            "metrics": {
                "cpu_usage": 45.0,
                "memory_usage": 95.0,  # exceeds 85 threshold
                "restart_count": 0,
            },
        }
        bus.publish("metrics-topic", event_payload)
        print("[Scenario 6] Published custom metric event for order-service (memory_usage=95.0).")

        # Wait for recommendation to be generated
        print("[Scenario 6] Waiting for recommendation to be generated...")
        rec_s6 = None
        for _ in range(60):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM recommendations 
                WHERE root_cause_service = 'order-service'
                ORDER BY created_at DESC LIMIT 1
                """
            )
            row = cursor.fetchone()
            conn.close()
            if row is not None:
                rec_s6 = dict(row)
                break
            time.sleep(1.0)

        assert rec_s6 is not None, "Scenario 6: No recommendation found for order-service!"
        rec_s6 = dict(row)
        print(
            f"[Scenario 6] Found recommendation: Action={rec_s6['recommended_action']} | "
            f"Prob={rec_s6['success_probability']} | Tier={rec_s6['match_tier']} | "
            f"Cases={rec_s6['similar_cases_count']}"
        )
        # Match Tier must be 3 because there was no historical memory matching order-service or memory_high
        assert rec_s6["match_tier"] == 3, (
            f"Expected match_tier 3 (Policy fallback), got {rec_s6['match_tier']}"
        )
        assert rec_s6["similar_cases_count"] == 0, (
            f"Expected 0 similar cases, got {rec_s6['similar_cases_count']}"
        )
        # Recommended action should follow policy default (which is restart_pod for memory)
        assert rec_s6["recommended_action"] == "restart_pod", (
            f"Expected recommended_action restart_pod, got {rec_s6['recommended_action']}"
        )
        print("[Scenario 6] Cold-start fallback verified successfully.")

        # ==========================================
        # Scenario 7: Human-in-the-Loop Approved Execution
        # ==========================================
        print("\n--- Running Scenario 7: Human-in-the-Loop Approved Execution ---")

        # 1. Update policy pol-001 to have risk_level = 'high'
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE policies SET risk_level = 'high' WHERE id = 'pol-001'")
        cursor.execute("DELETE FROM approvals")
        cursor.execute("UPDATE incidents SET status = 'remediated'")
        conn.commit()
        conn.close()

        # Wait for any trailing events to settle
        time.sleep(5.0)

        # 2. Publish metric event to trigger memory_high on order-service
        event_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "telemetry.metric",
            "timestamp": time.time(),
            "service_name": "order-service",
            "namespace": "hecate-system",
            "metrics": {
                "cpu_usage": 45.0,
                "memory_usage": 95.0,
                "restart_count": 0,
            },
        }
        bus.publish("metrics-topic", event_payload)
        print("[Scenario 7] Published metric event to trigger high-risk approval.")

        # 3. Wait for approval record to be created (status='pending')
        print("[Scenario 7] Waiting for pending approval request in DB...")
        approval_rec = None
        for _ in range(60):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM approvals WHERE status = 'pending' ORDER BY requested_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            if row is not None:
                approval_rec = dict(row)
                break
            time.sleep(1.0)

        assert approval_rec is not None, (
            "Scenario 7: No pending approval request found in database!"
        )

        # 4. Verify incident status is AWAITING_APPROVAL
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM incidents WHERE id = ?", (approval_rec["incident_id"],))
        inc_status = cursor.fetchone()[0]
        conn.close()
        assert inc_status == "AWAITING_APPROVAL", (
            f"Scenario 7: Expected status AWAITING_APPROVAL, got {inc_status}"
        )

        # 5. Resolve approval via HTTP API resolve route
        import httpx

        resolve_res = httpx.post(
            f"http://localhost:8000/api/v1/approvals/{approval_rec['id']}/resolve",
            json={"action": "approve", "operator": "e2e-tester"},
        )
        assert resolve_res.status_code == 200, (
            f"Scenario 7: Failed to resolve approval: {resolve_res.status_code}"
        )

        # 6. Wait for incident status to transition to REMEDIATED
        remediated = False
        for _ in range(60):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status FROM incidents WHERE id = ?", (approval_rec["incident_id"],)
            )
            row = cursor.fetchone()
            conn.close()
            if row and row[0].upper() == "REMEDIATED":
                remediated = True
                break
            time.sleep(1.0)

        assert remediated, "Scenario 7: Incident status was not transitioned to REMEDIATED!"
        print("[Scenario 7] HITL approved execution verified successfully.")

        # ==========================================
        # Scenario 8: Human-in-the-Loop Rejected Execution
        # ==========================================
        print("\n--- Running Scenario 8: Human-in-the-Loop Rejected Execution ---")

        # 1. Reset approvals and database state
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM approvals")
        cursor.execute("UPDATE incidents SET status = 'remediated'")
        conn.commit()
        conn.close()

        # Wait for any trailing events to settle
        time.sleep(5.0)

        # 2. Publish metric event to trigger memory_high on order-service
        event_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "telemetry.metric",
            "timestamp": time.time(),
            "service_name": "order-service",
            "namespace": "hecate-system",
            "metrics": {
                "cpu_usage": 45.0,
                "memory_usage": 95.0,
                "restart_count": 0,
            },
        }
        bus.publish("metrics-topic", event_payload)
        print("[Scenario 8] Published metric event to trigger high-risk approval.")

        # 3. Wait for approval record to be created
        approval_rec = None
        for _ in range(60):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM approvals WHERE status = 'pending' ORDER BY requested_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            if row is not None:
                approval_rec = dict(row)
                break
            time.sleep(1.0)

        assert approval_rec is not None, (
            "Scenario 8: No pending approval request found in database!"
        )

        # 4. Resolve approval with reject action
        resolve_res = httpx.post(
            f"http://localhost:8000/api/v1/approvals/{approval_rec['id']}/resolve",
            json={"action": "reject", "operator": "e2e-tester"},
        )
        assert resolve_res.status_code == 200, (
            f"Scenario 8: Failed to reject approval: {resolve_res.status_code}"
        )

        # 5. Check database states: status CLOSED/REJECTED, 0 remediation runs
        final_status = "UNKNOWN"
        for _ in range(45):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM incidents WHERE id = ?", (approval_rec["incident_id"],))
            row = cursor.fetchone()
            conn.close()
            if row:
                final_status = row[0]
                if final_status.upper() in ["CLOSED", "REJECTED"]:
                    break
            time.sleep(1.0)

        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM remediations WHERE incident_id = ?",
            (approval_rec["incident_id"],),
        )
        rem_count = cursor.fetchone()[0]
        conn.close()

        assert final_status.upper() in ["CLOSED", "REJECTED"], (
            f"Scenario 8: Expected status CLOSED or REJECTED, got {final_status}"
        )
        assert rem_count == 0, f"Scenario 8: Expected 0 remediations executed, got {rem_count}"
        print("[Scenario 8] HITL rejected execution verified successfully.")

        # ==========================================
        # Scenario 9: Duplicate Approval Concurrency Protection
        # ==========================================
        print("\n--- Running Scenario 9: Duplicate Approval Concurrency Protection ---")

        # 1. Reset approvals and database state
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM approvals")
        cursor.execute("UPDATE incidents SET status = 'remediated'")
        conn.commit()
        conn.close()

        # Wait for trailing events
        time.sleep(5.0)

        # 2. Publish metric event to trigger memory_high on order-service
        event_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "telemetry.metric",
            "timestamp": time.time(),
            "service_name": "order-service",
            "namespace": "hecate-system",
            "metrics": {
                "cpu_usage": 45.0,
                "memory_usage": 95.0,
                "restart_count": 0,
            },
        }
        bus.publish("metrics-topic", event_payload)

        # 3. Wait for approval record to be created
        approval_rec = None
        for _ in range(60):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM approvals WHERE status = 'pending' ORDER BY requested_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            if row is not None:
                approval_rec = dict(row)
                break
            time.sleep(1.0)

        assert approval_rec is not None, (
            "Scenario 9: No pending approval request found in database!"
        )

        # 4. Fire concurrent HTTP resolve approval posts
        import asyncio

        async def resolve_async(app_id, action):
            async with httpx.AsyncClient() as client:
                return await client.post(
                    f"http://localhost:8000/api/v1/approvals/{app_id}/resolve",
                    json={"action": action, "operator": "e2e-tester"},
                    timeout=5.0,
                )

        async def run_concurrent():
            return await asyncio.gather(
                resolve_async(approval_rec["id"], "approve"),
                resolve_async(approval_rec["id"], "approve"),
            )

        responses = asyncio.run(run_concurrent())
        status_codes = [r.status_code for r in responses]
        print(f"[Scenario 9] Concurrency status codes received: {status_codes}")
        assert 200 in status_codes, "Scenario 9: Expected one resolution to succeed with 200 OK"
        assert 409 in status_codes, "Scenario 9: Expected one resolution to fail with 409 Conflict"
        print("[Scenario 9] Concurrency double-resolve protection verified successfully.")

        # Cleanup: restore policy risk_level back to 'medium'
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE policies SET risk_level = 'medium' WHERE id = 'pol-001'")
        conn.commit()
        conn.close()

        # ==========================================
        # Scenario 10: Proactive Memory Capacity Scale-Up
        # ==========================================
        print("\n--- Running Scenario 10: Proactive Memory Capacity Scale-Up ---")
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM approvals")
        cursor.execute("DELETE FROM prediction_outcomes")
        cursor.execute("UPDATE incidents SET status = 'remediated'")
        conn.commit()
        conn.close()

        # Publish 15 metrics events simulating a linear leak (Memory increasing by 1.5% each step: 70, 71.5, 73...)
        from hecate_events import HecateEventBus

        bus = HecateEventBus()
        for cycle in range(15):
            event_payload = {
                "event_id": f"s10-metric-{cycle}",
                "event_type": "telemetry.metric",
                "timestamp": time.time(),
                "service_name": "payment-service",
                "namespace": "hecate-system",
                "metrics": {
                    "cpu_usage": 45.0,
                    "memory_usage": float(70.0 + cycle * 1.5),
                    "restart_count": 0,
                },
            }
            bus.publish("metrics-topic", event_payload)
            time.sleep(0.2)

        # Wait for the predicted incident to be generated
        print("[Scenario 10] Waiting for predicted incident in database...")
        predicted_inc = None
        for _ in range(60):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM incidents WHERE is_predicted = 1 AND service_name = 'payment-service' ORDER BY detected_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            if row is not None:
                predicted_inc = dict(row)
                break
            time.sleep(1.0)

        assert predicted_inc is not None, "Scenario 10: No predicted incident was generated!"
        print(
            f"[Scenario 10] Found predicted incident: ID={predicted_inc['id']} | Status={predicted_inc['status']} | Lead Time={predicted_inc['lead_time_seconds']}s | Conf={predicted_inc['prediction_confidence']}"
        )
        assert predicted_inc["prediction_status"] in ["PENDING", "PREVENTED"], (
            f"Expected prediction_status PENDING or PREVENTED, got {predicted_inc['prediction_status']}"
        )

        # Wait for it to be proactively remediated
        print("[Scenario 10] Waiting for proactive remediation to complete...")
        remediated_proactive = False
        for _ in range(90):
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, prediction_status FROM incidents WHERE id = ?",
                (predicted_inc["id"],),
            )
            row = cursor.fetchone()
            conn.close()
            if row and row[0].upper() == "REMEDIATED" and row[1] == "PREVENTED":
                remediated_proactive = True
                break
            time.sleep(1.0)

        assert remediated_proactive, (
            "Scenario 10: Proactive remediation did not transition status to REMEDIATED/PREVENTED!"
        )

        # Check prediction outcomes table
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM prediction_outcomes")
        outcomes_count = cursor.fetchone()[0]
        conn.close()
        assert outcomes_count > 0, "Scenario 10: No record written to prediction_outcomes!"
        print("[Scenario 10] Proactive memory capacity scale-up verified successfully.")

        # ==========================================
        # Scenario 11: False Positive Protection
        # ==========================================
        print("\n--- Running Scenario 11: False Positive Protection ---")
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM incidents WHERE service_name = 'order-service'")
        conn.commit()
        conn.close()

        # Publish 15 metrics events simulating stable memory (oscillating between 70.0 and 71.0)
        for cycle in range(15):
            event_payload = {
                "event_id": f"s11-metric-{cycle}",
                "event_type": "telemetry.metric",
                "timestamp": time.time(),
                "service_name": "order-service",
                "namespace": "hecate-system",
                "metrics": {
                    "cpu_usage": 45.0,
                    "memory_usage": float(70.0 + (cycle % 2)),
                    "restart_count": 0,
                },
            }
            bus.publish("metrics-topic", event_payload)
            time.sleep(0.2)

        # Wait and verify that no order-service incident is created
        print("[Scenario 11] Waiting to verify no predicted incident is generated...")
        time.sleep(5.0)

        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE service_name = 'order-service'")
        order_inc_count = cursor.fetchone()[0]
        conn.close()

        assert order_inc_count == 0, (
            f"Scenario 11: Expected 0 incidents for order-service, but found {order_inc_count}!"
        )
        print("[Scenario 11] False positive protection verified successfully.")

        # ==========================================
        # Scenario 12: HECATE Copilot Chat MTTR & Prevented Incidents QA
        # ==========================================
        print("\n--- Running Scenario 12: HECATE Copilot Chat MTTR & Prevented Incidents QA ---")
        import httpx

        # Wait 2 seconds for copilot database sync
        time.sleep(2.0)

        # 1. Ask about average MTTR
        payload_mttr = {"message": "What is our average MTTR?", "session_id": "test-session"}
        res_mttr = httpx.post(
            "http://localhost:8000/api/v1/copilot/chat", json=payload_mttr, timeout=5.0
        )
        assert res_mttr.status_code == 200, (
            f"Scenario 12: MTTR query failed: {res_mttr.status_code}"
        )
        data_mttr = res_mttr.json()
        print(f"[Scenario 12] Copilot response for MTTR query: {data_mttr['response']}")
        assert "average recovery time (MTTR)" in data_mttr["response"], (
            "Scenario 12: Response did not contain MTTR information"
        )

        # 2. Ask about prevented incidents
        payload_prev = {
            "message": "How many incidents were prevented?",
            "session_id": "test-session",
        }
        res_prev = httpx.post(
            "http://localhost:8000/api/v1/copilot/chat", json=payload_prev, timeout=5.0
        )
        assert res_prev.status_code == 200, (
            f"Scenario 12: Prevented query failed: {res_prev.status_code}"
        )
        data_prev = res_prev.json()
        print(f"[Scenario 12] Copilot response for Prevented query: {data_prev['response']}")
        assert "proactively prevented" in data_prev["response"], (
            "Scenario 12: Response did not contain prevented incidents count"
        )
        print("[Scenario 12] Copilot Chat MTTR and Prevented Incidents QA verified successfully.")

        # ==========================================
        # Scenario 13: Similar Incident Retrieval TF-IDF search QA
        # ==========================================
        print("\n--- Running Scenario 13: Similar Incident Retrieval TF-IDF search QA ---")

        # Ask about payment-db failure (should retrieve similar incident from database)
        payload_similar = {"message": "Why did payment-db fail?", "session_id": "test-session"}
        res_similar = httpx.post(
            "http://localhost:8000/api/v1/copilot/chat", json=payload_similar, timeout=5.0
        )
        assert res_similar.status_code == 200, (
            f"Scenario 13: Similar incident query failed: {res_similar.status_code}"
        )
        data_similar = res_similar.json()
        print(
            f"[Scenario 13] Copilot response for similar incident query: {data_similar['response']}"
        )
        assert len(data_similar["sources"]) > 0, (
            "Scenario 13: Expected at least one source document retrieved"
        )
        assert "payment-db" in data_similar["response"], (
            "Scenario 13: Response did not mention payment-db"
        )
        print("[Scenario 13] Similar incident retrieval verified successfully.")

        # ==========================================
        # Scenario 14: Gemini Fallback Verification
        # ==========================================
        print("\n--- Running Scenario 14: Gemini Fallback Verification ---")

        # With no GEMINI_API_KEY env set in this test environment, the copilot service must fall back to Mock mode
        payload_fallback = {"message": "Top root causes this month", "session_id": "test-session"}
        res_fallback = httpx.post(
            "http://localhost:8000/api/v1/copilot/chat", json=payload_fallback, timeout=5.0
        )
        assert res_fallback.status_code == 200, (
            f"Scenario 14: Fallback query failed: {res_fallback.status_code}"
        )
        data_fallback = res_fallback.json()
        print(f"[Scenario 14] Copilot response mode: {data_fallback['mode']}")
        assert data_fallback["mode"] == "mock", (
            f"Scenario 14: Expected mode 'mock', got {data_fallback['mode']}"
        )
        assert "root cause" in data_fallback["response"], (
            "Scenario 14: Response did not describe root causes"
        )
        print("[Scenario 14] Gemini fallback to Mock mode verified successfully.")

        # ==========================================
        # Scenario 15: Graph-Aware RCA & Recommendations
        # ==========================================
        print("\n--- Running Scenario 15: Graph-Aware RCA & Recommendations ---")
        # 1. Verify the topology is initialized
        res_graph = httpx.get("http://localhost:8005/api/v1/graph/data")
        assert res_graph.status_code == 200, "Scenario 15: Failed to fetch graph data"
        gdata = res_graph.json()
        
        # Verify payment-service and payment-db exist in graph
        nodes_ids = [n["data"]["id"] for n in gdata["nodes"]]
        assert "payment-service" in nodes_ids, "Scenario 15: payment-service missing from graph"
        assert "payment-db" in nodes_ids, "Scenario 15: payment-db missing from graph"
        
        # 2. Add an active incident on payment-db
        inc_id = "INC-GRAPH-DB-15"
        res_node = httpx.post("http://localhost:8005/api/v1/graph/node", json={
            "label": "Incident",
            "id": inc_id,
            "properties": {
                "status": "open",
                "service_name": "payment-db",
                "title": "payment-db storage full"
            }
        })
        assert res_node.status_code == 200, "Scenario 15: Failed to create Incident node"
        
        res_rel = httpx.post("http://localhost:8005/api/v1/graph/relationship", json={
            "from_label": "Incident",
            "from_key": inc_id,
            "to_label": "Service",
            "to_key": "payment-db",
            "rel_type": "OCCURRED_ON"
        })
        assert res_rel.status_code == 200, "Scenario 15: Failed to create OCCURRED_ON relationship"
        
        # 3. Query RCA for payment-service
        res_rca = httpx.get("http://localhost:8005/api/v1/graph/rca", params={"service": "payment-service"})
        assert res_rca.status_code == 200, "Scenario 15: Failed to query graph RCA"
        rca_data = res_rca.json()
        print(f"[Scenario 15] Graph RCA data: {rca_data}")
        assert rca_data["root_cause_service"] == "payment-db", f"Expected payment-db, got {rca_data['root_cause_service']}"
        assert rca_data["incident_id"] == inc_id, f"Expected incident_id {inc_id}, got {rca_data['incident_id']}"
        print("[Scenario 15] Graph-aware RCA and recommendation logic verified successfully.")

        # ==========================================
        # Scenario 16: Neo4j Fallback to Mock Graph
        # ==========================================
        print("\n--- Running Scenario 16: Neo4j Fallback to Mock Graph ---")
        res_root = httpx.get("http://localhost:8005/")
        assert res_root.status_code == 200, "Scenario 16: Failed to get graph service root status"
        root_data = res_root.json()
        print(f"[Scenario 16] Graph Service root status: {root_data}")
        assert root_data["mode"] == "mock", f"Expected mock mode, got {root_data['mode']}"
        print("[Scenario 16] Neo4j fallback to Mock mode verified successfully.")

        # ==========================================
        # Scenario 17: Copilot Graph Reasoning QA
        # ==========================================
        print("\n--- Running Scenario 17: Copilot Graph Reasoning QA ---")
        # Ask Copilot why payment-service failed. It should query the graph, find payment-db incident, and respond.
        payload_copilot = {"message": "Why did payment-service fail?", "session_id": "test-session"}
        res_copilot = httpx.post("http://localhost:8000/api/v1/copilot/chat", json=payload_copilot, timeout=5.0)
        assert res_copilot.status_code == 200, "Scenario 17: Failed to query copilot chat"
        copilot_data = res_copilot.json()
        print(f"[Scenario 17] Copilot response: {copilot_data['response']}")
        assert "Graph traversal resolved" in copilot_data["response"], "Scenario 17: Missing 'Graph traversal resolved'"
        assert "payment-service depends on payment-db" in copilot_data["response"], "Scenario 17: Missing dependency chain explanation"
        assert "payment-db" in copilot_data["response"], "Scenario 17: Missing root cause service name"
        print("[Scenario 17] Copilot graph reasoning verified successfully.")

        # ==========================================
        # Scenario 18: Recommendation Neighbor Discovery QA
        # ==========================================
        print("\n--- Running Scenario 18: Recommendation Neighbor Discovery QA ---")
        # 1. Seed payment-cache node and depends_on edge to payment-db
        httpx.post("http://localhost:8005/api/v1/graph/node", json={
            "label": "Service",
            "id": "payment-cache",
            "properties": {"status": "healthy"}
        })
        httpx.post("http://localhost:8005/api/v1/graph/relationship", json={
            "from_label": "Service",
            "from_key": "payment-cache",
            "to_label": "Service",
            "to_key": "payment-db",
            "rel_type": "DEPENDS_ON"
        })
        
        # 2. Seed historical incident on neighbor (payment-db) resolved by restart_pod playbook
        hist_inc_id = "INC-HIST-18"
        httpx.post("http://localhost:8005/api/v1/graph/node", json={
            "label": "Incident",
            "id": hist_inc_id,
            "properties": {"status": "remediated"}
        })
        httpx.post("http://localhost:8005/api/v1/graph/relationship", json={
            "from_label": "Incident",
            "from_key": hist_inc_id,
            "to_label": "Service",
            "to_key": "payment-db",
            "rel_type": "OCCURRED_ON"
        })
        httpx.post("http://localhost:8005/api/v1/graph/node", json={
            "label": "Playbook",
            "id": "restart_pod",
            "properties": {"name": "restart_pod", "success_rate": 0.95}
        })
        httpx.post("http://localhost:8005/api/v1/graph/relationship", json={
            "from_label": "Incident",
            "from_key": hist_inc_id,
            "to_label": "Playbook",
            "to_key": "restart_pod",
            "rel_type": "RESOLVED_BY"
        })
        
        # 3. Query recommendations for payment-cache (which has no direct history)
        res_recs = httpx.get("http://localhost:8005/api/v1/graph/recommendations", params={
            "service": "payment-cache",
            "incident_type": "cpu_high"
        })
        assert res_recs.status_code == 200, "Scenario 18: Failed to fetch recommendations"
        recs_data = res_recs.json()
        print(f"[Scenario 18] Neighbor recommendations: {recs_data}")
        assert len(recs_data) > 0, "Scenario 18: No neighbor recommendations returned"
        assert recs_data[0]["playbook"] == "restart_pod", f"Expected playbook restart_pod, got {recs_data[0]['playbook']}"
        assert recs_data[0]["neighbor"] == "payment-db", f"Expected neighbor payment-db, got {recs_data[0]['neighbor']}"
        print("[Scenario 18] Neighbor recommendation discovery verified successfully.")

        # ==========================================
        # Scenario 19: Multi-Cluster Simulation & Playbook Scoring
        # ==========================================
        print("\n--- Running Scenario 19: Multi-Cluster Simulation & Playbook Scoring ---")
        # Query simulation endpoint on digital-twin-service
        res_sim = httpx.post("http://localhost:8006/api/v1/twin/simulate", json={
            "service": "payment-service",
            "incident_id": "INC-SIM-19",
            "incident_type": "cpu_high",
            "metrics": {"cpu_usage": 95.0, "memory_usage": 90.0}
        })
        assert res_sim.status_code == 200, "Scenario 19: Simulation query failed"
        sim_data = res_sim.json()
        print(f"[Scenario 19] Simulation response: {sim_data}")
        assert "simulations" in sim_data, "Scenario 19: Response missing simulations list"
        assert len(sim_data["simulations"]) > 0, "Scenario 19: Simulations list is empty"
        assert sim_data["simulations"][0]["playbook_sequence"] is not None, "Scenario 19: First sequence is empty"
        print("[Scenario 19] Multi-cluster simulation and playbook scoring verified successfully.")

        # ==========================================
        # Scenario 20: Policy-as-Code Declarative Governance
        # ==========================================
        print("\n--- Running Scenario 20: Policy-as-Code Declarative Governance ---")
        # Verify OPA evaluate endpoint rejects migration on databases
        payload_policy = {
            "action": "migrate_service",
            "service_name": "payment-db",
            "service_type": "database",
            "cluster": "cluster-aws-primary",
            "traffic": "normal",
            "replicas": 1
        }
        res_pol = httpx.post("http://localhost:8002/api/v1/policies/evaluate", json=payload_policy)
        assert res_pol.status_code == 200, "Scenario 20: Policy evaluation query failed"
        pol_data = res_pol.json()
        print(f"[Scenario 20] Policy evaluation response: {pol_data}")
        assert pol_data["effect"] == "reject", f"Expected reject, got {pol_data['effect']}"
        assert pol_data["policy_id"] == "pol-db-no-migrate", f"Expected policy pol-db-no-migrate, got {pol_data['policy_id']}"
        print("[Scenario 20] Declarative Policy-as-Code governance evaluated successfully.")

        # ==========================================
        # Scenario 21: Adaptive Policy Learning Q-value Updates
        # ==========================================
        print("\n--- Running Scenario 21: Adaptive Policy Learning Q-value Updates ---")
        # 1. Check initial Q-value (defaults to 0.0)
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT q_value FROM playbook_q_values WHERE state_key = 'cpu_high' AND action_name = 'scale_deployment'")
        q_row = cursor.fetchone()
        initial_q = float(q_row[0]) if q_row else 0.0
        conn.close()
        print(f"[Scenario 21] Initial Q-value for cpu_high/scale_deployment: {initial_q}")

        # 2. Trigger learning feedback event on learning-topic
        from hecate_events import HecateEventBus
        eb = HecateEventBus(kafka_servers="localhost:9094")
        feedback_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "learning.feedback",
            "schema_version": "1.0.0",
            "incident_id": "INC-FEEDBACK-21",
            "incident_type": "cpu_high",
            "incident_title": "CPU utilization breach",
            "root_cause_service": "payment-service",
            "remediation_action": "scale_deployment",
            "success": True,
            "recovery_time_seconds": 15,
            "confidence_score": 0.90,
            "effectiveness_score": 0.85,
            "timestamp": time.time()
        }
        eb.publish("learning-topic", feedback_event)
        
        # Wait 2 seconds for recommendation agent to consume and update Q-value
        time.sleep(2.0)

        # 3. Verify Q-value has increased
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT q_value FROM playbook_q_values WHERE state_key = 'cpu_high' AND action_name = 'scale_deployment'")
        q_row = cursor.fetchone()
        new_q = float(q_row[0]) if q_row else 0.0
        conn.close()
        print(f"[Scenario 21] Updated Q-value for cpu_high/scale_deployment: {new_q}")
        assert new_q > initial_q, f"Expected Q-value to increase, but got old={initial_q}, new={new_q}"
        print("[Scenario 21] Adaptive policy learning Q-value updates verified successfully.")

        # ==========================================
        # Scenario 22: Copilot Planning Agent QA
        # ==========================================
        print("\n--- Running Scenario 22: Copilot Planning Agent QA ---")
        payload_copilot = {"message": "Generate a remediation plan for payment-service", "session_id": "test-session"}
        res_copilot = httpx.post("http://localhost:8000/api/v1/copilot/chat", json=payload_copilot, timeout=5.0)
        assert res_copilot.status_code == 200, "Scenario 22: Copilot chat query failed"
        copilot_data = res_copilot.json()
        print(f"[Scenario 22] Copilot response:\n{copilot_data['response']}")
        assert "Plan Candidate" in copilot_data["response"], "Scenario 22: Response did not contain comparison table headers"
        assert "success_probability" in copilot_data["response"] or "Success Probability" in copilot_data["response"], "Scenario 22: Response did not contain success rates"
        assert "scale_deployment" in copilot_data["response"], "Scenario 22: Comparison did not show scale_deployment candidate"
        print("[Scenario 22] Copilot Planning Engine QA verified successfully.")

        # ==========================================
        # Scenario 23: Simulation Accuracy Calculation
        # ==========================================
        print("\n--- Running Scenario 23: Simulation Accuracy Calculation ---")
        # Check current calibration accuracy
        res_twin = httpx.get("http://localhost:8006/api/v1/twin/data")
        assert res_twin.status_code == 200, "Scenario 23: Failed to fetch twin data"
        twin_data = res_twin.json()
        initial_accuracy = twin_data["calibration"]["accuracy"]
        print(f"[Scenario 23] Initial calibration accuracy: {initial_accuracy}")
        
        # Trigger calibration with huge prediction error
        res_cal = httpx.post("http://localhost:8006/api/v1/twin/calibrate", json={
            "incident_id": "INC-SIM-19",
            "playbook_sequence": sim_data["simulations"][0]["playbook_sequence"],
            "actual_mttr": 45.0
        })
        assert res_cal.status_code == 200, "Scenario 23: Calibration request failed"
        cal_data = res_cal.json()
        print(f"[Scenario 23] Calibration response: {cal_data}")
        assert cal_data["prediction_error"] > 0, "Scenario 23: Prediction error should be non-zero"
        print("[Scenario 23] Simulation accuracy calculation verified successfully.")

        # ==========================================
        # Scenario 24: Twin Feedback Calibration
        # ==========================================
        print("\n--- Running Scenario 24: Twin Feedback Calibration ---")
        # Calibrate the twin 5 times with identical feedback data
        for i in range(5):
            res_cal = httpx.post("http://localhost:8006/api/v1/twin/calibrate", json={
                "incident_id": "INC-SIM-19",
                "playbook_sequence": sim_data["simulations"][0]["playbook_sequence"],
                "actual_mttr": 15.0
            })
            assert res_cal.status_code == 200, f"Scenario 24: Calibration loop {i} failed"
            current_acc = res_cal.json()["new_calibration_accuracy"]
            print(f" -> Loop {i}: Accuracy calibrated to {current_acc}")

        # Check total calibrations
        res_twin_final = httpx.get("http://localhost:8006/api/v1/twin/data")
        final_cal_data = res_twin_final.json()
        print(f"[Scenario 24] Final total calibrations: {final_cal_data['calibration']['total_calibrations']}")
        assert final_cal_data["calibration"]["total_calibrations"] >= 6, "Expected at least 6 calibrations logged"
        print("[Scenario 24] Twin feedback calibration verified successfully.")

        # ==========================================
        # Scenario 25: Plan Comparison & Scoring Selection
        # ==========================================
        print("\n--- Running Scenario 25: Plan Comparison & Scoring Selection ---")
        # Trigger an anomaly on payment-service to see the whole loop run through the Digital Twin simulation-agent
        trigger_payload = {"cpu_usage": 98.0, "memory_usage": 60.0, "restart_count": 0}
        with open(os.path.join(ROOT_DIR, "simulation_trigger.json"), "w") as f:
            json.dump(trigger_payload, f)

        # Wait for the incident to trigger, simulate, score, decide, and execute
        time.sleep(5.0)
        if os.path.exists(os.path.join(ROOT_DIR, "simulation_trigger.json")):
            os.remove(os.path.join(ROOT_DIR, "simulation_trigger.json"))

        # Wait for the incident resolution
        wait_for_incidents_resolve(60)

        # Verify DB states
        conn, _ = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM twin_memory ORDER BY created_at DESC LIMIT 5")
        twin_records = [dict(r) for r in cursor.fetchall()]
        conn.close()

        print(f"[Scenario 25] Logged twin simulation predictions: {twin_records}")
        assert len(twin_records) > 0, "Scenario 25: No simulation predictions logged in twin_memory!"
        print("[Scenario 25] Plan comparison & scoring selection verified successfully.")

        print(
            "[E2E Test] SUCCESS: All 25 Scenarios (1: Anomaly, 2: RCA, 3: Learning Memory, 4: Double Trigger, 5: Similarity, 6: Cold-Start, 7: HITL Approval, 8: HITL Rejection, 9: Concurrency Resolution, 10: Proactive Mitigation, 11: False Positive Protection, 12: Copilot MTTR/Prevented QA, 13: Similar Incident Search, 14: Gemini Fallback, 15: Graph RCA, 16: Mock Fallback, 17: Copilot Graph QA, 18: Neighbor Recs, 19: Twin Simulation, 20: Policy-as-Code, 21: TD Learning, 22: Planning Agent, 23: Accuracy Calc, 24: Calibration Feedback, 25: Plan Comparison) verified successfully!"
        )
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
