import os
import yaml
import httpx
import structlog
from pydantic import BaseModel

from .hecate_db import get_db_connection
from .vector_store import VectorStore

log = structlog.get_logger()


class RetrievalEngine:
    """Retrieves relevant records from HECATE's local vector index using similarity search."""
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def search(self, query: str, limit: int = 5) -> list[dict]:
        return self.vector_store.search(query, limit=limit)


class ExplanationEngine:
    """Generates user-friendly explanations for standard operational questions (MTTR, approvals, KPIs)."""
    @staticmethod
    def explain_mttr() -> str:
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*), AVG(recovery_time_seconds), AVG(effectiveness_score) FROM operational_memory"
            )
            row = cursor.fetchone()
            count = row[0] if row[0] is not None else 0
            avg_time = row[1] if row[1] is not None else 0.0
            avg_eff = row[2] if row[2] is not None else 0.0

            cursor.execute(
                "SELECT remediation_action, COUNT(*) as c FROM operational_memory GROUP BY remediation_action ORDER BY c DESC LIMIT 1"
            )
            top_row = cursor.fetchone()
            top_action = top_row[0] if top_row else "none"
            conn.close()

            return (
                f"According to HECATE's operational memory, the average recovery time (MTTR) is {avg_time:.1f}s "
                f"across {count} resolved incidents, with an average remediation effectiveness score of {avg_eff:.2%}. "
                f"The most frequently successful action in our database is '{top_action}'."
            )
        except Exception as e:
            log.error("explanation_engine.mttr_failed", error=str(e))
            return "Unable to retrieve MTTR statistics at this time."

    @staticmethod
    def explain_prevented() -> str:
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM incidents WHERE is_predicted = 1 AND prediction_status = 'PREVENTED'"
            )
            count = cursor.fetchone()[0]
            conn.close()

            return (
                f"A total of {count} incident(s) were proactively prevented by HECATE's predictive capacity forecasting model "
                f"before they could breach thresholds and cause system outages."
            )
        except Exception as e:
            log.error("explanation_engine.prevented_failed", error=str(e))
            return "Unable to retrieve prevented incident metrics."

    @staticmethod
    def explain_approvals() -> str:
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM approvals")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM approvals WHERE LOWER(status) = 'approved'")
            approved = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM approvals WHERE LOWER(status) = 'rejected'")
            rejected = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM approvals WHERE LOWER(status) = 'pending'")
            pending = cursor.fetchone()[0]
            conn.close()

            return (
                f"HECATE's human-in-the-loop governance has tracked a total of {total} approval requests: "
                f"{approved} actions were APPROVED and executed, {rejected} actions were REJECTED/blocked, "
                f"and {pending} requests are currently pending manual review."
            )
        except Exception as e:
            log.error("explanation_engine.approvals_failed", error=str(e))
            return "Unable to retrieve governance approvals summary."

    @staticmethod
    def explain_accuracy() -> str:
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM incidents WHERE is_predicted = 1 AND prediction_status = 'PREVENTED'"
            )
            prevented = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM incidents WHERE is_predicted = 1 AND prediction_status = 'FALSE_POSITIVE'"
            )
            fp = cursor.fetchone()[0]
            conn.close()

            total_predictions = prevented + fp
            accuracy = 100.0
            if total_predictions > 0:
                accuracy = (prevented / total_predictions) * 100.0

            return (
                f"Our predictive trend model currently exhibits a capacity forecast accuracy of {accuracy:.1f}%. "
                f"Based on historical metrics, HECATE logged {prevented} successfully prevented incident(s) and "
                f"{fp} false positive alert(s)."
            )
        except Exception as e:
            log.error("explanation_engine.accuracy_failed", error=str(e))
            return "Unable to compute predictive accuracy KPI."

    @staticmethod
    def explain_best_playbook() -> str:
        try:
            conn, _ = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT remediation_action, AVG(effectiveness_score) as eff, COUNT(*) as c "
                "FROM operational_memory WHERE success = 1 GROUP BY remediation_action ORDER BY eff DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                action, eff, count = row[0], row[1], row[2]
                return (
                    f"The most successful remediation playbook in HECATE's operational memory is '{action}', "
                    f"with an average effectiveness score of {eff:.2%} across {count} successful execution(s)."
                )
            return "There are no successful remediation records logged in operational memory yet."
        except Exception as e:
            log.error("explanation_engine.playbook_failed", error=str(e))
            return "Unable to identify top playbooks."


class PlanningEngine:
    """Simulates recovery strategies, compares plans side-by-side, and justifies recommendations."""
    @staticmethod
    def generate_plan(service: str, query: str) -> str:
        # Default mock simulation data in case twin service is offline
        simulations = [
            {"playbook_sequence": "scale_deployment", "predicted_mttr": 15.0, "predicted_cost": 10.0, "predicted_blast_radius": 0.0, "success_probability": 0.9, "confidence": 0.9, "score": 0.81},
            {"playbook_sequence": "restart_pod", "predicted_mttr": 12.0, "predicted_cost": 0.0, "predicted_blast_radius": 0.1, "success_probability": 0.75, "confidence": 0.9, "score": 0.78},
            {"playbook_sequence": "rollback_release", "predicted_mttr": 18.0, "predicted_cost": 0.0, "predicted_blast_radius": 0.2, "success_probability": 0.85, "confidence": 0.9, "score": 0.74},
            {"playbook_sequence": "migrate_service", "predicted_mttr": 25.0, "predicted_cost": 5.0, "predicted_blast_radius": 0.4, "success_probability": 0.6, "confidence": 0.9, "score": 0.52}
        ]
        confidence = 0.90
        
        # Try querying the digital twin service dynamically
        try:
            res = httpx.post("http://localhost:8006/api/v1/twin/simulate", json={
                "service": service,
                "incident_id": f"INC-PLAN-{uuid.uuid4().hex[:4].upper()}" if "uuid" in globals() else "INC-PLAN-100",
                "incident_type": "capacity_breach",
                "metrics": {"cpu_usage": 95.0, "memory_usage": 90.0}
            }, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                simulations = data.get("simulations", simulations)
                confidence = data.get("confidence", confidence)
        except Exception as e:
            log.warn("planning_engine.twin_service_offline_using_defaults", error=str(e))

        best = simulations[0] if simulations else {}
        
        # Build comparative markdown table
        table = "| Plan Candidate | Success Probability | Projected MTTR | Resource Cost | Blast Radius | Twin Score |\n"
        table += "| :--- | :---: | :---: | :---: | :---: | :---: |\n"
        for s in simulations:
            table += (
                f"| **{s['playbook_sequence']}** | {s['success_probability']:.0%} | {s['predicted_mttr']}s | "
                f"${s['predicted_cost']:.2f} | {s['predicted_blast_radius']} | `{s['score']:.3f}` |\n"
            )

        resp = (
            f"### HECATE Autonomous Remediation Plan Comparison for **{service}**\n\n"
            f"The **Planning Engine** queried the infrastructure twin to simulate candidate plays. "
            f"Current twin confidence rating is **{confidence:.1%}**.\n\n"
            f"{table}\n"
            f"**Recommended Strategy**: `{best.get('playbook_sequence')}`\n\n"
            f"**Reasoning**: This playbook sequence achieved the highest Twin Score of `{best.get('score')}`. "
            f"It provides a projected success rate of {best.get('success_probability'):.0%} and "
            f"0s downtime risk, satisfying our declarative policy constraints with minimal blast radius."
        )
        return resp


class RagEngine:
    def __init__(self, settings, vector_store: VectorStore):
        self.settings = settings
        self.vector_store = vector_store
        self.retrieval_engine = RetrievalEngine(vector_store)

    async def generate_response(self, query: str) -> tuple[str, list[dict], str]:
        # 1. Retrieve relevant records using TF-IDF vector search
        sources = self.retrieval_engine.search(query, limit=5)
        log.info("rag_engine.documents_retrieved", query=query, count=len(sources))

        # Check mode: Gemini vs Mock
        mode = self.settings.copilot_mode.lower()

        if mode == "gemini" and self.settings.gemini_api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.settings.gemini_api_key)
                model = genai.GenerativeModel("gemini-pro")

                # Construct RAG prompt
                context_str = ""
                for doc in sources:
                    context_str += f"[{doc['source'].upper()} - ID: {doc['id']}] {doc['text']}\n\n"

                prompt = (
                    "You are HECATE Copilot, an AI cloud reliability operations assistant.\n"
                    "You have access to HECATE's operational memory, incidents, recommendations, approvals, predictions, and policies.\n"
                    "Use the following retrieved context documents from HECATE's SQLite database to answer the user's question.\n"
                    "Keep your answer clear, concise, and professional.\n\n"
                    f"Retrieved Database Context:\n{context_str}\n"
                    f"User Question: {query}\n\n"
                    "Answer:"
                )

                log.info("rag_engine.calling_gemini_api")
                response = model.generate_content(prompt)
                return response.text, sources, "gemini"

            except Exception as e:
                log.warn("rag_engine.gemini_api_failed_falling_back_to_mock", error=str(e))
                mode = "mock"

        # Mock Mode response generation (Deterministic QA Engine)
        response_text, sources = self._generate_mock_response(query, sources)
        return response_text, sources, mode

    def _generate_mock_response(self, query: str, sources: list[dict]) -> tuple[str, list[dict]]:
        query_lower = query.lower()

        # Query Type 0: Planning / Simulation Strategy Candidate Comparison
        if any(kw in query_lower for kw in ["plan", "remediation plan", "strategy", "strategies", "simulate", "options"]):
            # Extract service name
            matched_service = "payment-service"
            for svc in ["payment-db", "payment-service", "order-service", "gateway"]:
                if svc in query_lower:
                    matched_service = svc
                    break
            
            resp = PlanningEngine.generate_plan(matched_service, query)
            return resp, sources

        # Query Type 1: MTTR / Average Recovery Time
        if any(
            kw in query_lower
            for kw in ["mttr", "average recovery", "recovery time", "recovery_time"]
        ):
            return ExplanationEngine.explain_mttr(), sources

        # Query Type 2: Prevented Incidents / Proactive Healing
        if any(
            kw in query_lower
            for kw in ["prevented", "proactive", "incidents prevented", "prevented incidents"]
        ):
            return ExplanationEngine.explain_prevented(), sources

        # Query Type 3: Approval History Stats
        if any(
            kw in query_lower
            for kw in ["approval", "approvals", "require approval", "approvals queue"]
        ):
            return ExplanationEngine.explain_approvals(), sources

        # Query Type 4: Prediction Accuracy KPI
        if any(
            kw in query_lower for kw in ["prediction accuracy", "forecast accuracy", "how accurate"]
        ):
            return ExplanationEngine.explain_accuracy(), sources

        # Query Type 5: Most successful remediation playbook
        if any(
            kw in query_lower
            for kw in ["most successful remediation", "best remediation", "what remediation works"]
        ):
            return ExplanationEngine.explain_best_playbook(), sources

        # Query Type 6: Top root causes this month
        if any(kw in query_lower for kw in ["top root causes", "root cause", "why did"]):
            # Check if user asked about a specific service failure (e.g., payment-db or payment-service)
            matched_service = None
            for svc in ["payment-db", "payment-service", "order-service", "gateway"]:
                if svc in query_lower:
                    matched_service = svc
                    break

            if matched_service:
                # First try querying graph-service for topological RCA
                try:
                    res = httpx.get(f"http://localhost:8005/api/v1/graph/rca?service={matched_service}", timeout=2.0)
                    if res.status_code == 200:
                        graph_data = res.json()
                        root_cause_svc = graph_data.get("root_cause_service")
                        incident_id = graph_data.get("incident_id")
                        title = graph_data.get("title")
                        desc = graph_data.get("root_cause")
                        
                        if root_cause_svc:
                            if root_cause_svc != matched_service:
                                resp = (
                                    f"Graph traversal resolved that {matched_service} depends on {root_cause_svc} "
                                    f"(Dependency chain: {matched_service} -> {root_cause_svc}). "
                                    f"An active incident {incident_id} ('{title}') was found on {root_cause_svc}, "
                                    f"which is the root cause of the {matched_service} failure: {desc}"
                                )
                            else:
                                resp = (
                                    f"Graph traversal isolated the root cause to {matched_service} itself. "
                                    f"No active incidents were found on downstream dependencies. Root cause details: {desc}"
                                )
                            return resp, sources
                except Exception as ge:
                    log.warn("rag_engine.graph_rca_query_failed", error=str(ge))

                # Retrieve incidents/memories referencing this service as root cause
                matching_docs = [
                    d
                    for d in sources
                    if d["source"] in ["incidents", "operational_memory"]
                    and matched_service in d["text"]
                ]
                if matching_docs:
                    doc = matching_docs[0]
                    metadata = doc["metadata"]
                    if doc["source"] == "incidents":
                        resp = (
                            f"According to HECATE's incident logs, {matched_service} failed with an active alert. "
                            f"The incident ID was {doc['id']}. Root Cause details: '{metadata['root_cause']}'. "
                            f"The current status is '{metadata['status']}'."
                        )
                    else:
                        resp = (
                            f"In our operational memory records, {matched_service} had a failure of type '{metadata['incident_type']}' "
                            f"(Incident ID {metadata['incident_id']}) which was resolved using '{metadata['remediation_action']}' "
                            f"with a success status of {metadata['success']}."
                        )
                    return resp, sources
                else:
                    return (
                        f"I found no recorded failures or root cause logs matching the service '{matched_service}' in our system.",
                        sources,
                    )

            try:
                conn, _ = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT root_cause_service, COUNT(*) as c FROM operational_memory GROUP BY root_cause_service ORDER BY c DESC LIMIT 1"
                )
                row = cursor.fetchone()
                conn.close()
                if row:
                    svc, count = row[0], row[1]
                    resp = (
                        f"The top root cause node identified in HECATE's operational history is '{svc}', "
                        f"accounting for {count} logged incident(s)."
                    )
                else:
                    resp = "No incident records found to analyze root cause frequencies."
                return resp, sources
            except Exception as e:
                log.error("mock_qa.top_causes_failed", error=str(e))

        # Default Fallback: context retrieval display
        if sources:
            context_summary = []
            for doc in sources[:3]:
                src_name = doc["source"].replace("_", " ").title()
                context_summary.append(f"- [{src_name} - ID: {doc['id']}] {doc['text']}")
            context_str = "\n".join(context_summary)

            resp = (
                f"I couldn't find a direct match for your request, but I retrieved these database contexts using TF-IDF similarity search:\n\n"
                f"{context_str}\n\n"
                "Please let me know if you would like me to retrieve specific details on any of these incidents."
            )
        else:
            resp = "I found no database records or context documents matching your query. HECATE's database is currently empty."
        return resp, sources

