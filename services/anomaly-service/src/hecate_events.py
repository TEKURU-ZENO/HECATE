import sqlite3
import json
import time
import os
import structlog

log = structlog.get_logger()

# Hardcoded absolute path for monorepo-wide consistency
DB_PATH = r"c:\Users\Dev Mehta\Desktop\HECATE\hecate_events.db"

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
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=1000,
                max_block_ms=1000
            )
            self.use_kafka = True
            log.info("event_bus.connected_to_kafka", servers=kafka_servers)
        except Exception as e:
            _kafka_disabled = True
            log.warn("event_bus.kafka_connection_failed_falling_back_to_sqlite", error=str(e), db_path=DB_PATH)
            self._init_sqlite()

    def _init_sqlite(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def publish(self, topic: str, payload: dict):
        global _kafka_disabled
        if self.use_kafka and not _kafka_disabled:
            try:
                self.producer.send(topic, payload)
                self.producer.flush()
                log.info("event_bus.published_to_kafka", topic=topic, evt_id=payload.get("event_id") or payload.get("id"))
                return
            except Exception as e:
                _kafka_disabled = True
                log.warn("event_bus.kafka_publish_failed_falling_to_sqlite", error=str(e))
                self._init_sqlite()
                self.use_kafka = False
        
        # SQLite publish
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO events (topic, payload) VALUES (?, ?)", (topic, json.dumps(payload)))
        conn.commit()
        conn.close()
        log.info("event_bus.published_to_sqlite", topic=topic, evt_id=payload.get("event_id") or payload.get("id") or payload.get("incident_id"))

    def subscribe(self, topics: list[str], group_id: str):
        global _kafka_disabled
        if self.use_kafka and not _kafka_disabled:
            try:
                from kafka import KafkaConsumer
                consumer = KafkaConsumer(
                    *topics,
                    bootstrap_servers=self.kafka_servers,
                    group_id=group_id,
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True
                )
                log.info("event_bus.kafka_subscriber_started", topics=topics, group_id=group_id)
                for message in consumer:
                    yield message.value
                return
            except Exception as e:
                _kafka_disabled = True
                log.warn("event_bus.kafka_subscribe_failed_falling_to_sqlite", error=str(e))
                self.use_kafka = False
        
        # SQLite subscribe loop
        self._init_sqlite()
        log.info("event_bus.sqlite_subscriber_started", topics=topics, group_id=group_id)
        
        # Start reading from the end of the DB
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM events")
        row = cursor.fetchone()
        last_id = row[0] if row[0] is not None else 0
        conn.close()
        
        while True:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, topic, payload FROM events WHERE id > ? ORDER BY id ASC", 
                (last_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                event_id, topic, payload = row
                last_id = event_id
                if topic in topics:
                    try:
                        yield json.loads(payload)
                    except Exception as e:
                        log.error("event_bus.sqlite_payload_parse_error", error=str(e))
            
            time.sleep(0.5)
