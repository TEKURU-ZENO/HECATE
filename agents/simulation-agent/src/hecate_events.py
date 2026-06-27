import json
import os
import sqlite3
import time

import structlog

log = structlog.get_logger()

# Resolve database path dynamically to support cross-platform monorepo environments
DB_PATH = os.environ.get("HECATE_EVENTS_DB_PATH")
if not DB_PATH:
    # Traverse directories upward to locate the repository root containing ROADMAP.md
    current_dir = os.path.abspath(os.path.dirname(__file__))
    while current_dir and current_dir != os.path.dirname(current_dir):
        if os.path.exists(os.path.join(current_dir, "ROADMAP.md")) or os.path.exists(os.path.join(current_dir, ".git")):
            DB_PATH = os.path.join(current_dir, "hecate_events.db")
            break
        current_dir = os.path.dirname(current_dir)
    if not DB_PATH:
        DB_PATH = "hecate_events.db"

_kafka_disabled = False


class HecateEventBus:
    def __init__(self, kafka_servers="localhost:9094", client_id="hecate-client"):
        global _kafka_disabled
        self.kafka_servers = kafka_servers
        self.client_id = client_id
        self.use_kafka = False
        self.producer = None

        if os.environ.get("HECATE_EVENT_ENGINE") == "sqlite" or _kafka_disabled:
            self._init_sqlite()
            return

        # Try to connect to Kafka
        try:
            from kafka import KafkaProducer

            self.producer = KafkaProducer(
                bootstrap_servers=kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                request_timeout_ms=1000,
                max_block_ms=1000,
            )
            self.use_kafka = True
            log.info("event_bus.connected_to_kafka", servers=kafka_servers)
        except Exception as e:
            _kafka_disabled = True
            log.warn(
                "event_bus.kafka_connection_failed_falling_back_to_sqlite",
                error=str(e),
                db_path=DB_PATH,
            )
            self._init_sqlite()

    def _init_sqlite(self):
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        conn.commit()
        conn.close()

    def publish(self, topic: str, payload: dict):
        # Tracing context propagation injection
        if "trace_context" not in payload:
            import uuid
            payload["trace_context"] = {
                "trace_id": os.environ.get("HECATE_ACTIVE_TRACE_ID") or uuid.uuid4().hex,
                "span_id": uuid.uuid4().hex[:16],
                "parent_span_id": os.environ.get("HECATE_ACTIVE_SPAN_ID") or ""
            }
        
        # Cryptographic signing for decision payloads (Phase P5 Security)
        if topic == "decision-topic":
            import hmac
            import hashlib
            secret_key = os.environ.get("DECISION_SIGNING_KEY", "HECATE_SECRET_SIGNING_KEY_2026").encode()
            payload_to_sign = {k: v for k, v in payload.items() if k not in ["signature", "trace_context"]}
            serialized_payload = json.dumps(payload_to_sign, sort_keys=True).encode()
            signature = hmac.new(secret_key, serialized_payload, hashlib.sha256).hexdigest()
            payload["signature"] = signature
        global _kafka_disabled
        if self.use_kafka and not _kafka_disabled:
            try:
                self.producer.send(topic, payload)
                self.producer.flush()
                log.info(
                    "event_bus.published_to_kafka",
                    topic=topic,
                    evt_id=payload.get("event_id") or payload.get("id"),
                )
                return
            except Exception as e:
                _kafka_disabled = True
                log.warn("event_bus.kafka_publish_failed_falling_to_sqlite", error=str(e))
                self._init_sqlite()
                self.use_kafka = False

        # SQLite publish
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        cursor.execute(
            "INSERT INTO events (topic, payload) VALUES (?, ?)", (topic, json.dumps(payload))
        )
        conn.commit()
        conn.close()
        log.info(
            "event_bus.published_to_sqlite",
            topic=topic,
            evt_id=payload.get("event_id") or payload.get("id") or payload.get("incident_id"),
        )

    def subscribe(self, topics: list[str], group_id: str):
        global _kafka_disabled
        if self.use_kafka and not _kafka_disabled:
            try:
                from kafka import KafkaConsumer

                consumer = KafkaConsumer(
                    *topics,
                    bootstrap_servers=self.kafka_servers,
                    group_id=group_id,
                    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                )
                log.info("event_bus.kafka_subscriber_started", topics=topics, group_id=group_id)
                for message in consumer:
                    evt = message.value
                    if isinstance(evt, dict):
                        trace_ctx = evt.get("trace_context")
                        if trace_ctx:
                            os.environ["HECATE_ACTIVE_TRACE_ID"] = trace_ctx.get("trace_id", "")
                            os.environ["HECATE_ACTIVE_SPAN_ID"] = trace_ctx.get("span_id", "")
                    yield evt
                return
            except Exception as e:
                _kafka_disabled = True
                log.warn("event_bus.kafka_subscribe_failed_falling_to_sqlite", error=str(e))
                self.use_kafka = False

        # SQLite subscribe loop
        self._init_sqlite()
        log.info("event_bus.sqlite_subscriber_started", topics=topics, group_id=group_id)

        # Start reading from the end of the DB
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        cursor.execute("SELECT MAX(id) FROM events")
        row = cursor.fetchone()
        last_id = row[0] if row[0] is not None else 0
        conn.close()

        while True:
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            cursor = conn.cursor()
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except Exception:
                pass
            cursor.execute(
                "SELECT id, topic, payload FROM events WHERE id > ? ORDER BY id ASC", (last_id,)
            )
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                event_id, topic, payload = row
                last_id = event_id
                if topic in topics:
                    try:
                        evt = json.loads(payload)
                        if isinstance(evt, dict):
                            trace_ctx = evt.get("trace_context")
                            if trace_ctx:
                                os.environ["HECATE_ACTIVE_TRACE_ID"] = trace_ctx.get("trace_id", "")
                                os.environ["HECATE_ACTIVE_SPAN_ID"] = trace_ctx.get("span_id", "")
                        yield evt
                    except Exception as e:
                        log.error("event_bus.sqlite_payload_parse_error", error=str(e))

            time.sleep(0.5)
