import structlog

from .hecate_db import get_db_connection
from .vector_store import VectorStore

log = structlog.get_logger()


class RagEngine:
    def __init__(self, settings, vector_store: VectorStore):
        self.settings = settings
        self.vector_store = vector_store

    async def generate_response(self, query: str) -> tuple[str, list[dict], str]:
        # 1. Retrieve relevant records using TF-IDF vector search
        sources = self.vector_store.search(query, limit=5)
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
        return response_text, sources, "mock"

    def _generate_mock_response(self, query: str, sources: list[dict]) -> tuple[str, list[dict]]:
        query_lower = query.lower()

        conn, _ = get_db_connection()
        cursor = conn.cursor()

        # Query Type 1: MTTR / Average Recovery Time
        if any(
            kw in query_lower
            for kw in ["mttr", "average recovery", "recovery time", "recovery_time"]
        ):
            try:
                cursor.execute(
                    "SELECT COUNT(*), AVG(recovery_time_seconds), AVG(effectiveness_score) FROM operational_memory"
                )
                row = cursor.fetchone()
                count = row[0] if row[0] is not None else 0
                avg_time = row[1] if row[1] is not None else 0.0
                avg_eff = row[2] if row[2] is not None else 0.0

                # Top action
                cursor.execute(
                    "SELECT remediation_action, COUNT(*) as c FROM operational_memory GROUP BY remediation_action ORDER BY c DESC LIMIT 1"
                )
                top_row = cursor.fetchone()
                top_action = top_row[0] if top_row else "none"

                conn.close()

                resp = (
                    f"According to HECATE's operational memory, the average recovery time (MTTR) is {avg_time:.1f}s "
                    f"across {count} resolved incidents, with an average remediation effectiveness score of {avg_eff:.2%}. "
                    f"The most frequently successful action in our database is '{top_action}'."
                )
                return resp, sources
            except Exception as e:
                log.error("mock_qa.mttr_failed", error=str(e))

        # Query Type 2: Prevented Incidents / Proactive Healing
        if any(
            kw in query_lower
            for kw in ["prevented", "proactive", "incidents prevented", "prevented incidents"]
        ):
            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM incidents WHERE is_predicted = 1 AND prediction_status = 'PREVENTED'"
                )
                count = cursor.fetchone()[0]
                conn.close()

                resp = (
                    f"A total of {count} incident(s) were proactively prevented by HECATE's predictive capacity forecasting model "
                    f"before they could breach thresholds and cause system outages."
                )
                return resp, sources
            except Exception as e:
                log.error("mock_qa.prevented_failed", error=str(e))

        # Query Type 3: Approval History Stats
        if any(
            kw in query_lower
            for kw in ["approval", "approvals", "require approval", "approvals queue"]
        ):
            try:
                cursor.execute("SELECT COUNT(*) FROM approvals")
                total = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM approvals WHERE LOWER(status) = 'approved'")
                approved = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM approvals WHERE LOWER(status) = 'rejected'")
                rejected = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM approvals WHERE LOWER(status) = 'pending'")
                pending = cursor.fetchone()[0]
                conn.close()

                resp = (
                    f"HECATE's human-in-the-loop governance has tracked a total of {total} approval requests: "
                    f"{approved} actions were APPROVED and executed, {rejected} actions were REJECTED/blocked, "
                    f"and {pending} requests are currently pending manual review."
                )
                return resp, sources
            except Exception as e:
                log.error("mock_qa.approvals_failed", error=str(e))

        # Query Type 4: Prediction Accuracy KPI
        if any(
            kw in query_lower for kw in ["prediction accuracy", "forecast accuracy", "how accurate"]
        ):
            try:
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

                resp = (
                    f"Our predictive trend model currently exhibits a capacity forecast accuracy of {accuracy:.1f}%. "
                    f"Based on historical metrics, HECATE logged {prevented} successfully prevented incident(s) and "
                    f"{fp} false positive alert(s)."
                )
                return resp, sources
            except Exception as e:
                log.error("mock_qa.accuracy_failed", error=str(e))

        # Query Type 5: Most successful remediation playbook
        if any(
            kw in query_lower
            for kw in ["most successful remediation", "best remediation", "what remediation works"]
        ):
            try:
                cursor.execute(
                    "SELECT remediation_action, AVG(effectiveness_score) as eff, COUNT(*) as c "
                    "FROM operational_memory WHERE success = 1 GROUP BY remediation_action ORDER BY eff DESC LIMIT 1"
                )
                row = cursor.fetchone()
                conn.close()
                if row:
                    action, eff, count = row[0], row[1], row[2]
                    resp = (
                        f"The most successful remediation playbook in HECATE's operational memory is '{action}', "
                        f"with an average effectiveness score of {eff:.2%} across {count} successful execution(s)."
                    )
                else:
                    resp = "There are no successful remediation records logged in operational memory yet."
                return resp, sources
            except Exception as e:
                log.error("mock_qa.success_remediation_failed", error=str(e))

        # Query Type 6: Top root causes this month
        if any(kw in query_lower for kw in ["top root causes", "root cause", "why did"]):
            # Check if user asked about a specific service failure (e.g., payment-db or payment-service)
            matched_service = None
            for svc in ["payment-db", "payment-service", "order-service", "gateway"]:
                if svc in query_lower:
                    matched_service = svc
                    break

            if matched_service:
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
                    conn.close()
                    return (
                        f"I found no recorded failures or root cause logs matching the service '{matched_service}' in our system.",
                        sources,
                    )

            try:
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
        conn.close()
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
