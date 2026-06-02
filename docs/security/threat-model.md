# Threat Model for HECATE
* Assets: Kubernetes credentials, Telemetry streams, PostgreSQL backend.
* Threats: Unauthorized policy modifications, metric poisoning.
* Mitigations: TLS 1.3, strict RBAC, network policies.