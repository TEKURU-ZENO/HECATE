import argparse
import json
import os

# Simulation trigger utility for HECATE

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRIGGER_FILE = os.path.join(ROOT_DIR, "simulation_trigger.json")

def main():
    parser = argparse.ArgumentParser(description="HECATE Simulation Trigger Injector")
    parser.add_argument("--cpu", type=float, help="Simulate specific CPU percentage (e.g. 95.0)")
    parser.add_argument("--memory", type=float, help="Simulate specific Memory percentage (e.g. 90.0)")
    parser.add_argument("--restarts", type=int, help="Simulate container restart count (e.g. 6)")
    parser.add_argument("--clear", action="store_true", help="Remove active trigger, return to baseline")

    args = parser.parse_args()

    if args.clear:
        if os.path.exists(TRIGGER_FILE):
            os.remove(TRIGGER_FILE)
            print("[Simulation] Active trigger cleared. Telemetry returning to healthy baseline.")
        else:
            print("[Simulation] No active triggers found.")
        return

    payload = {}
    if args.cpu is not None:
        payload["cpu_usage"] = args.cpu
    if args.memory is not None:
        payload["memory_usage"] = args.memory
    if args.restarts is not None:
        payload["restart_count"] = args.restarts

    if not payload:
        print("[Simulation] Warning: No metrics provided. Provide at least one parameter.")
        return

    with open(TRIGGER_FILE, "w") as f:
        json.dump(payload, f)

    print(f"[Simulation] Trigger injected successfully: {payload}")

if __name__ == "__main__":
    main()
