# ADR-001: Event-Driven Architecture
* **Status**: Accepted
* **Context**: Agents require asynchronous decoupling and horizontal scalability to process high-throughput metric streams.
* **Decision**: Implement an event-driven design using Kafka for inter-agent communication.
* **Consequences**: Enhanced fault tolerance, scalability, and loose agent coupling.