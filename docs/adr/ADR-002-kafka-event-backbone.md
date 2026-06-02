# ADR-002: Kafka Event Backbone
* **Status**: Accepted
* **Context**: Need a message log that supports high throughput, persistence, and consumer-group scaling.
* **Decision**: Deploy Apache Kafka in KRaft mode for local and production message routing.
* **Consequences**: Assures at-least-once message delivery, ordering by partition keys, and system replayability.