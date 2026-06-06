import os
import time
import uuid
import yaml
import structlog
from datetime import datetime

from .config import Settings
from .hecate_events import HecateEventBus
from .hecate_db import get_db_connection
from .dependency_resolver import DependencyResolver

log = structlog.get_logger()

class RcaAgent:
    """HECATE RCA Agent — Builds graph topology to find root cause of anomalies core logic class."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._running = False
        self.event_bus = HecateEventBus(kafka_servers=settings.kafka_bootstrap_servers)
        
        # Load topology and construct graph
        topology_cfg = self._load_topology()
        self.graph = DependencyResolver.load_graph(topology_cfg)
        log.info("rca_agent.initialized", nodes=list(self.graph.nodes), edges=list(self.graph.edges))

    def _load_topology(self) -> dict:
        ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        rules_path = os.path.join(ROOT_DIR, "policies", "default-rules.yaml")
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r") as f:
                    data = yaml.safe_load(f)
                return data.get("topology", {})
            except Exception as e:
                log.error("rca_agent.topology_load_failed", error=str(e))
        return {}

    async def run(self) -> None:
        self._running = True
        log.info("rca_agent.started")
        
        # Subscribe to incident-topic
        for incident in self.event_bus.subscribe(["incident-topic"], group_id="rca-group"):
            if not self._running:
                break
            try:
                await self.process_incident(incident)
            except Exception as e:
                log.error("rca_agent.processing_failed", error=str(e))

    async def process_incident(self, incident: dict) -> None:
        start_time = time.time()
        incident_id = incident.get("incident_id")
        anomaly_id = incident.get("anomaly_id")
        service_name = incident.get("service_name")
        namespace = incident.get("namespace")
        title = incident.get("title")
        
        log.info("rca_agent.received_incident", incident_id=incident_id, service=service_name)
        
        # 1. Resolve downstream dependencies using DependencyResolver
        downstream = DependencyResolver.get_downstream_dependencies(self.graph, service_name)
        log.info("rca_agent.downstream_resolved", service=service_name, downstream=downstream)
        
        # 2. Query DB to check if any downstream service has an active alert
        root_cause_service = service_name
        confidence_score = 0.70
        risk_score = 0.40
        root_cause_description = f"Self-contained alert in {service_name}."
        
        try:
            conn, use_pg = get_db_connection()
            cursor = conn.cursor()
            
            # Fetch active incidents
            if use_pg:
                cursor.execute("SELECT service_name, title FROM incidents WHERE status NOT IN ('remediated', 'closed') AND id != %s", (incident_id,))
            else:
                cursor.execute("SELECT service_name, title FROM incidents WHERE status NOT IN ('remediated', 'closed') AND id != ?", (incident_id,))
                
            rows = cursor.fetchall()
            conn.close()
            
            active_services = {row[0]: row[1] for row in rows}
            log.info("rca_agent.active_db_alerts", active_services=list(active_services.keys()))
            
            # Cross reference downstream nodes with active database incidents
            for ds_svc in downstream:
                if ds_svc in active_services:
                    root_cause_service = ds_svc
                    confidence_score = 0.95
                    risk_score = 0.85
                    root_cause_description = f"{service_name} failure caused by downstream service {root_cause_service} alert."
                    break
        except Exception as e:
            log.error("rca_agent.db_query_failed_using_self", error=str(e))
            
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 3. Update Incident record in database with RCA details
        try:
            conn, use_pg = get_db_connection()
            cursor = conn.cursor()
            if use_pg:
                cursor.execute(
                    "UPDATE incidents SET root_cause = %s, confidence_score = %s, risk_score = %s WHERE id = %s",
                    (root_cause_description, confidence_score, risk_score, incident_id)
                )
            else:
                cursor.execute(
                    "UPDATE incidents SET root_cause = ?, confidence_score = ?, risk_score = ? WHERE id = ?",
                    (root_cause_description, confidence_score, risk_score, incident_id)
                )
            conn.commit()
            conn.close()
            log.info("rca_agent.db_updated", incident_id=incident_id, root_cause=root_cause_service)
        except Exception as e:
            log.error("rca_agent.db_update_failed", error=str(e))
            
        # 4. Construct and publish RCAEvent matching schema
        affected = [service_name]
        upstream = DependencyResolver.get_upstream_dependencies(self.graph, service_name)
        affected.extend(upstream)
        
        rca_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "rca.completed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "incident_id": incident_id,
            "anomaly_id": anomaly_id,
            "analysis_duration_ms": duration_ms,
            "rca_result": {
                "root_cause_service": root_cause_service,
                "root_cause_description": root_cause_description,
                "affected_services": affected,
                "dependency_path": [service_name, root_cause_service] if root_cause_service != service_name else [service_name],
                "confidence_score": confidence_score,
                "risk_score": risk_score,
                "failure_mode": "resource_exhaustion" if "db" in root_cause_service else "cascading_failure" if root_cause_service != service_name else "unknown",
                "evidence": [
                    {
                        "type": "dependency_graph",
                        "description": f"Traversed topology downstream of {service_name}. Detected downstream dependency {root_cause_service} is active." if root_cause_service != service_name else f"No active downstream anomalies detected for {service_name}."
                    }
                ]
            },
            "schema_version": "1.0.0"
        }
        
        log.info("rca_agent.diagnosed", root_cause=root_cause_service, confidence=confidence_score)
        self.event_bus.publish("rca-topic", rca_payload)

    async def stop(self) -> None:
        self._running = False
        log.info("rca_agent.stopped")

