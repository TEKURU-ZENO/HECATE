# ADR-004: Multi-Agent Design
* **Status**: Accepted
* **Context**: Decoupling detection, diagnosis, decisions, and execution logic isolates concerns.
* **Decision**: Implement 7 distinct agents: monitoring, detection, rca, decision, remediation, learning, and reporting.
* **Consequences**: Clean separation of operational logic, but increases message routing overhead.