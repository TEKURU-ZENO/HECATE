import re
import time

import numpy as np
import structlog

from .hecate_db import get_db_connection

log = structlog.get_logger()


class VectorStore:
    def __init__(self, index_refresh_interval: int = 60):
        self.index_refresh_interval = index_refresh_interval
        self.last_rebuild_time = 0.0

        # In-memory document storage
        self.documents = []  # List of dict: {"id": str, "text": str, "source": str, "metadata": dict}
        self.vocab = {}  # dict: word -> index
        self.idf = []  # list/array of IDF weights
        self.doc_vectors = None  # numpy array of shape (num_docs, vocab_size)

        # Basic english stopwords
        self.stopwords = {
            "a",
            "about",
            "above",
            "after",
            "again",
            "against",
            "all",
            "am",
            "an",
            "and",
            "any",
            "are",
            "arent",
            "as",
            "at",
            "be",
            "because",
            "been",
            "before",
            "being",
            "below",
            "between",
            "both",
            "but",
            "by",
            "cant",
            "cannot",
            "could",
            "couldnt",
            "did",
            "didnt",
            "do",
            "does",
            "doesnt",
            "doing",
            "dont",
            "down",
            "during",
            "each",
            "few",
            "for",
            "from",
            "further",
            "had",
            "hadnt",
            "has",
            "hasnt",
            "have",
            "havent",
            "having",
            "he",
            "hed",
            "hell",
            "hes",
            "her",
            "here",
            "heres",
            "hers",
            "herself",
            "him",
            "himself",
            "his",
            "how",
            "hows",
            "i",
            "id",
            "im",
            "ive",
            "if",
            "in",
            "into",
            "is",
            "isnt",
            "it",
            "its",
            "itself",
            "lets",
            "me",
            "more",
            "most",
            "mustnt",
            "my",
            "myself",
            "no",
            "nor",
            "not",
            "of",
            "off",
            "on",
            "once",
            "only",
            "or",
            "other",
            "ought",
            "our",
            "ours",
            "ourselves",
            "out",
            "over",
            "own",
            "same",
            "shant",
            "she",
            "shed",
            "shell",
            "shes",
            "should",
            "shouldnt",
            "so",
            "some",
            "such",
            "than",
            "that",
            "thats",
            "the",
            "their",
            "theirs",
            "them",
            "themselves",
            "then",
            "there",
            "theres",
            "these",
            "they",
            "theyd",
            "theyll",
            "theyre",
            "theyve",
            "this",
            "those",
            "through",
            "to",
            "too",
            "under",
            "until",
            "up",
            "very",
            "was",
            "wasnt",
            "we",
            "wed",
            "well",
            "were",
            "weve",
            "werent",
            "what",
            "whats",
            "when",
            "whens",
            "where",
            "wheres",
            "which",
            "while",
            "who",
            "whos",
            "whom",
            "why",
            "whys",
            "with",
            "wont",
            "would",
            "wouldnt",
            "you",
            "youd",
            "youll",
            "youre",
            "youve",
            "your",
            "yours",
            "yourself",
            "yourselves",
        }

    def tokenize(self, text: str) -> list[str]:
        # Lowercase, keep alphanumeric words
        text = text.lower()
        words = re.findall(r"\b[a-z0-9_\-\.]+\b", text)
        return [w for w in words if w not in self.stopwords]

    def rebuild_index(self):
        start_time = time.time()
        log.info("vector_store.rebuilding_index")

        conn, _ = get_db_connection()
        if not conn:
            log.error("vector_store.db_connection_failed")
            return

        cursor = conn.cursor()
        new_documents = []

        # 1. Fetch Incidents
        try:
            cursor.execute("SELECT * FROM incidents")
            rows = cursor.fetchall()
            for r in rows:
                meta = dict(r)
                text = (
                    f"Incident ID {meta['id']} code {meta['incident_code']} title: {meta['title']}. "
                    f"Severity: {meta['severity']}. Status: {meta['status']}. "
                    f"Service Name: {meta['service_name']}. Resolved Root Cause: {meta['root_cause']}. "
                    f"Risk Score: {meta.get('risk_score', 0.0)}. Predicted Anomaly: {meta.get('is_predicted', 0)}. "
                    f"Prediction Status: {meta.get('prediction_status', 'NONE')}."
                )
                new_documents.append(
                    {"id": meta["id"], "text": text, "source": "incidents", "metadata": meta}
                )
        except Exception as e:
            log.error("vector_store.fetch_incidents_failed", error=str(e))

        # 2. Fetch Operational Memory
        try:
            cursor.execute("SELECT * FROM operational_memory")
            rows = cursor.fetchall()
            for r in rows:
                meta = dict(r)
                text = (
                    f"Operational Memory ID {meta['id']} incident_id {meta['incident_id']}. "
                    f"Type: {meta['incident_type']}. Title: {meta['incident_title']}. "
                    f"Root Cause Service: {meta['root_cause_service']}. Remediation Action: {meta['reremediation_action'] if 'reremediation_action' in meta else meta.get('remediation_action', '')}. "
                    f"Success Status: {meta['success']}. Recovery Time: {meta['recovery_time_seconds']} seconds. "
                    f"Effectiveness Score: {meta['effectiveness_score']}."
                )
                new_documents.append(
                    {
                        "id": meta["id"],
                        "text": text,
                        "source": "operational_memory",
                        "metadata": meta,
                    }
                )
        except Exception as e:
            log.error("vector_store.fetch_memory_failed", error=str(e))

        # 3. Fetch Approvals
        try:
            cursor.execute("SELECT * FROM approvals")
            rows = cursor.fetchall()
            for r in rows:
                meta = dict(r)
                text = (
                    f"Approval ID {meta['id']} incident_id {meta['incident_id']}. "
                    f"Incident Type: {meta['incident_type']}. Recommended Action: {meta['recommended_action']}. "
                    f"Root Cause Service: {meta['root_cause_service']}. Risk Level: {meta['risk_level']}. "
                    f"Recommendation Score: {meta['recommendation_score']}. Decision Status: {meta['status']}. "
                    f"Approval Reason: {meta['approval_reason']}. Decided by: {meta['decided_by']}."
                )
                new_documents.append(
                    {"id": meta["id"], "text": text, "source": "approvals", "metadata": meta}
                )
        except Exception as e:
            log.error("vector_store.fetch_approvals_failed", error=str(e))

        # 4. Fetch Prediction Outcomes
        try:
            cursor.execute("SELECT * FROM prediction_outcomes")
            rows = cursor.fetchall()
            for r in rows:
                meta = dict(r)
                text = (
                    f"Prediction Outcome ID {meta['id']} incident_id {meta['incident_id']}. "
                    f"Confidence: {meta['prediction_confidence']}. Lead Time: {meta['lead_time_seconds']} seconds. "
                    f"Predicted: {meta['predicted']}. Actually Occurred: {meta['actually_occurred']}."
                )
                new_documents.append(
                    {
                        "id": meta["id"],
                        "text": text,
                        "source": "prediction_outcomes",
                        "metadata": meta,
                    }
                )
        except Exception as e:
            log.error("vector_store.fetch_prediction_outcomes_failed", error=str(e))

        # 5. Fetch Policies
        try:
            cursor.execute("SELECT * FROM policies")
            rows = cursor.fetchall()
            for r in rows:
                meta = dict(r)
                text = (
                    f"Policy ID {meta['id']} Name: {meta['policy_name']}. "
                    f"Condition Expression: {meta['condition_expression']}. Action Definition: {meta['action_definition']}. "
                    f"Risk Level: {meta['risk_level']}. Enabled: {meta['enabled']}."
                )
                new_documents.append(
                    {"id": meta["id"], "text": text, "source": "policies", "metadata": meta}
                )
        except Exception as e:
            log.error("vector_store.fetch_policies_failed", error=str(e))

        # 6. Fetch Recommendations
        try:
            cursor.execute("SELECT * FROM recommendations")
            rows = cursor.fetchall()
            for r in rows:
                meta = dict(r)
                text = (
                    f"Recommendation ID {meta['id']} incident_id {meta['incident_id']}. "
                    f"Incident Type: {meta['incident_type']}. Root Cause Service: {meta['root_cause_service']}. "
                    f"Recommended Action: {meta['recommended_action']}. Playbook Success Probability: {meta['success_probability']}. "
                    f"Average Effectiveness: {meta['avg_effectiveness']}. Total Score: {meta['recommendation_score']}. "
                    f"Match Tier: {meta['match_tier']}. Similar Cases Count: {meta['similar_cases_count']}."
                )
                new_documents.append(
                    {"id": meta["id"], "text": text, "source": "recommendations", "metadata": meta}
                )
        except Exception as e:
            log.error("vector_store.fetch_recommendations_failed", error=str(e))

        conn.close()

        # Build TF-IDF Vocabulary and Vectors
        if not new_documents:
            self.documents = []
            self.vocab = {}
            self.idf = []
            self.doc_vectors = None
            self.last_rebuild_time = time.time()
            log.info("vector_store.rebuild_completed_empty")
            return

        # 1. Build Vocab & Tokenize documents
        doc_tokens = []
        vocab_set = set()
        for doc in new_documents:
            tokens = self.tokenize(doc["text"])
            doc_tokens.append(tokens)
            vocab_set.update(tokens)

        vocab = {word: idx for idx, word in enumerate(sorted(list(vocab_set)))}
        vocab_size = len(vocab)
        num_docs = len(new_documents)

        # 2. Compute Document Frequencies & IDF
        df = np.zeros(vocab_size)
        for tokens in doc_tokens:
            unique_tokens = set(tokens)
            for t in unique_tokens:
                if t in vocab:
                    df[vocab[t]] += 1

        # Smooth IDF
        idf = np.log((1 + num_docs) / (1 + df)) + 1

        # 3. Compute TF-IDF Vectors for each document
        doc_vectors = np.zeros((num_docs, vocab_size))
        for d_idx, tokens in enumerate(doc_tokens):
            if not tokens:
                continue
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            for t, count in tf.items():
                if t in vocab:
                    v_idx = vocab[t]
                    # Normalized Term Frequency
                    tf_val = count / len(tokens)
                    doc_vectors[d_idx, v_idx] = tf_val * idf[v_idx]

        self.documents = new_documents
        self.vocab = vocab
        self.idf = idf
        self.doc_vectors = doc_vectors
        self.last_rebuild_time = time.time()
        log.info(
            "vector_store.rebuild_completed",
            num_docs=num_docs,
            vocab_size=vocab_size,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    def maybe_rebuild_index(self):
        if time.time() - self.last_rebuild_time > self.index_refresh_interval:
            self.rebuild_index()

    def search(self, query: str, limit: int = 5) -> list[dict]:
        self.maybe_rebuild_index()

        if not self.documents or self.doc_vectors is None or not self.vocab:
            return []

        # Vectorize query
        q_tokens = self.tokenize(query)
        q_vector = np.zeros(len(self.vocab))
        if not q_tokens:
            # Fallback to returning recent documents if query is empty
            return self.documents[:limit]

        tf = {}
        for t in q_tokens:
            tf[t] = tf.get(t, 0) + 1

        for t, count in tf.items():
            if t in self.vocab:
                v_idx = self.vocab[t]
                tf_val = count / len(q_tokens)
                q_vector[v_idx] = tf_val * self.idf[v_idx]

        # Calculate cosine similarity
        q_norm = np.linalg.norm(q_vector)
        if q_norm == 0:
            # No vocab overlap
            return []

        # Vectorized cosine similarity computation
        doc_norms = np.linalg.norm(self.doc_vectors, axis=1)
        # Avoid division by zero
        doc_norms[doc_norms == 0] = 1.0

        similarities = np.dot(self.doc_vectors, q_vector) / (doc_norms * q_norm)

        # Sort matching indices
        top_indices = np.argsort(similarities)[::-1][:limit]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.0:  # Only return documents with some similarity overlap
                results.append(
                    {
                        "id": self.documents[idx]["id"],
                        "text": self.documents[idx]["text"],
                        "source": self.documents[idx]["source"],
                        "metadata": self.documents[idx]["metadata"],
                        "score": score,
                    }
                )
        return results
