import os
import sys
import time
import unittest
import uuid

# Add workspace root to python path to import helpers
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from hecate_db import get_db_connection
from hecate_events import HecateEventBus


class TestHecateMonorepo(unittest.TestCase):

    def test_event_bus_pub_sub(self):
        """Verify HecateEventBus can publish and receive messages."""
        bus = HecateEventBus()
        test_topic = f"test-topic-{uuid.uuid4().hex[:6]}"
        test_payload = {"id": str(uuid.uuid4()), "message": "HECATE Integration Check"}

        # Publish in a separate thread after subscriber is active
        import threading
        def delayed_publish():
            time.sleep(1.0)
            bus.publish(test_topic, test_payload)

        t = threading.Thread(target=delayed_publish, daemon=True)
        t.start()

        # Subscribe and read with timeout
        received = []
        subscriber = bus.subscribe([test_topic], group_id="test-group")

        # Run consumer in short loop
        start_time = time.time()
        for msg in subscriber:
            received.append(msg)
            if len(received) >= 1:
                break
            if time.time() - start_time > 4.0:
                break

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["message"], "HECATE Integration Check")

    def test_database_initialization(self):
        """Verify db connection helper initializes and accesses tables."""
        conn, use_pg = get_db_connection()
        self.assertIsNotNone(conn)

        cursor = conn.cursor()

        # Write a test incident
        inc_id = f"INC-TEST-{uuid.uuid4().hex[:6]}"
        title = "Test Incident"
        severity = "medium"
        status = "open"
        service_name = "test-service"

        if use_pg:
            cursor.execute(
                "INSERT INTO incidents (id, incident_code, title, severity, status, service_name, detected_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                (inc_id, inc_id, title, severity, status, service_name)
            )
        else:
            cursor.execute(
                "INSERT INTO incidents (id, incident_code, title, severity, status, service_name) VALUES (?, ?, ?, ?, ?, ?)",
                (inc_id, inc_id, title, severity, status, service_name)
            )

        conn.commit()

        # Retrieve it
        cursor.execute("SELECT title, severity, status FROM incidents WHERE id = ?", (inc_id,))
        row = dict(cursor.fetchone())
        self.assertEqual(row["title"], "Test Incident")
        self.assertEqual(row["severity"], "medium")
        self.assertEqual(row["status"], "open")

        # Clean up test entry
        cursor.execute("DELETE FROM incidents WHERE id = ?", (inc_id,))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    unittest.main()
