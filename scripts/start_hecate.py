import os
import signal
import subprocess
import sys
import time

# HECATE Monorepo process orchestrator

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
processes = []


def cleanup():
    print("\\n[Orchestrator] Stopping all HECATE services and agents...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    print("[Orchestrator] Stopped.")


def main():
    # Clean previous local DB caches to start fresh
    db_paths = [
        os.path.join(ROOT_DIR, "hecate_db.sqlite"),
        os.path.join(ROOT_DIR, "hecate_events.db"),
    ]
    for db in db_paths:
        if os.path.exists(db):
            try:
                os.remove(db)
                print(f"[Orchestrator] Cleaned cache database: {os.path.basename(db)}")
            except Exception as e:
                print(f"[Orchestrator] Warning: could not clear {db}: {e}")

    # Set up signal handler
    def sig_handler(sig, frame):
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    print("[Orchestrator] Starting HECATE Core platform services...")

    # 1. Services configs
    services = [
        {"name": "dashboard-api", "path": "services/dashboard-api", "port": 8000},
        {"name": "anomaly-service", "path": "services/anomaly-service", "port": 8001},
        {"name": "policy-service", "path": "services/policy-service", "port": 8002},
    ]

    for svc in services:
        print(f" -> Launching {svc['name']} on http://localhost:{svc['port']}")
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.main:app", "--port", str(svc["port"])],
            cwd=os.path.join(ROOT_DIR, svc["path"]),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(p)

    time.sleep(2)  # Allow services to initialize their DB states

    print("[Orchestrator] Starting HECATE Operational Agents...")
    agents = [
        {"name": "monitoring-agent", "path": "agents/monitoring-agent"},
        {"name": "detection-agent", "path": "agents/detection-agent"},
        {"name": "rca-agent", "path": "agents/rca-agent"},
        {"name": "recommendation-agent", "path": "agents/recommendation-agent"},
        {"name": "decision-agent", "path": "agents/decision-agent"},
        {"name": "remediation-agent", "path": "agents/remediation-agent"},
        {"name": "learning-agent", "path": "agents/learning-agent"},
    ]

    for ag in agents:
        print(f" -> Launching {ag['name']} operational loop")
        p = subprocess.Popen(
            [sys.executable, "-m", "src.main"],
            cwd=os.path.join(ROOT_DIR, ag["path"]),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(p)

    print("[Orchestrator] HECATE platform is fully running locally.")
    print(" -> Frontend React URL: http://localhost:3000")
    print(" -> Main dashboard API: http://localhost:8000/docs")
    print("Press Ctrl+C to terminate the platform.")

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
