# ADR-003: Kubernetes Runtime
* **Status**: Accepted
* **Context**: The target workloads run on Kubernetes, and HECATE should run alongside them for native API access.
* **Decision**: Package all agents as containerized deployments running on EKS/Kubernetes.
* **Consequences**: Integrates with Kubernetes RBAC, ServiceAccounts, and facilitates auto-scaling.