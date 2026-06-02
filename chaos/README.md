# HECATE Chaos Engineering

> **Validate HECATE's self-healing capabilities under real failure conditions.**

Chaos engineering is a disciplined approach to improving system resilience by intentionally introducing failures and verifying that the system responds as expected. HECATE uses [LitmusChaos](https://litmuschaos.io/) to orchestrate experiments against the Kubernetes cluster.

---

## Purpose

- **Verify self-healing**: Confirm that HECATE agents detect and remediate failures automatically within SLO targets
- **Find hidden weaknesses**: Expose dependencies, race conditions, and failure modes not caught by unit/integration tests
- **Build confidence**: Demonstrate that autonomous remediation works reliably before critical incidents occur in production
- **Measure MTTR**: Quantify how quickly HECATE can detect, diagnose, and recover from various failure types

---

## Chaos Engineering Principles

1. **Start in staging**: Never run destructive experiments in production without prior staging validation
2. **Define steady state first**: Know what "normal" looks like before injecting failures (see steady state hypotheses)
3. **Minimize blast radius**: Start with small percentages (`PODS_AFFECTED_PERC: 10`) and increase gradually
4. **Abort on breach**: Configure automatic rollback if steady state is violated beyond acceptable bounds
5. **Observe everything**: All experiments should have full Prometheus/Grafana/Jaeger observability active
6. **Document findings**: Record outcomes, MTTR measurements, and gaps discovered in each runbook

---

## Safety Guidelines

> [!CAUTION]
> All chaos experiments can cause real service disruptions. Follow these rules strictly.

- **Require approval** for any experiment above 30% `PODS_AFFECTED_PERC`
- **Notify the team** via `#hecate-chaos` Slack channel before running experiments
- **Verify rollback** procedures work before starting an experiment
- **Never run** network partition or node-kill experiments without an on-call engineer present
- **Monitor Grafana** dashboards throughout the experiment duration
- **Stop immediately** if the blast radius exceeds expectations

---

## Experiment Catalog

| Experiment | Scenario | Target | Duration | Severity |
|-----------|---------|--------|----------|----------|
| `pod-kill.yaml` | Kill 50% of pods | `hecate-agents` | 30s | Medium |
| `cpu-hog.yaml` | CPU exhaustion | Any pod | 60s | High |
| `network-latency.yaml` | 500ms latency injection | Service mesh | 60s | Medium |
| `memory-hog.yaml` | Memory pressure | Any pod | 60s | High |
| `payment-service-kill.yaml` | Kill payment service | `payment-service` | 30s | Critical |
| `redis-saturation.yaml` | Redis memory saturation | `redis` | 120s | High |

---

## Running an Experiment

```bash
# 1. Ensure LitmusChaos operator is installed
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v3.0.0.yaml

# 2. Apply the ChaosExperiment definition
kubectl apply -f chaos/scenarios/pod-kill.yaml

# 3. Apply the ChaosEngine (triggers the experiment)
kubectl apply -f chaos/experiments/payment-service-kill.yaml

# 4. Monitor the experiment
kubectl describe chaosengine payment-service-kill -n hecate-system
kubectl logs -n hecate-system -l name=chaos-runner -f

# 5. Retrieve results
kubectl describe chaosresult payment-service-kill-pod-delete -n hecate-system
```

---

## Steady State Hypothesis Template

Every experiment must define a steady state hypothesis:
```yaml
steadyStateHypothesis:
  title: "Services are healthy and HECATE is responsive"
  probes:
    - name: "API error rate below 1%"
      type: promProbe
      mode: Continuous
      promProbe/inputs:
        endpoint: "http://prometheus:9090"
        query: "rate(http_requests_total{status=~'5..'}[1m]) < 0.01"
    - name: "HECATE detection agent is running"
      type: k8sProbe
      mode: Edge
      k8sProbe/inputs:
        resource: "pod"
        namespace: "hecate-agents"
        labelSelector: "app=detection-agent"
```

---

## Observing Results

After each experiment, check:
1. **Grafana** → `HECATE — Service Health` dashboard for error rate spikes
2. **Grafana** → `HECATE — Incident Overview` for auto-triggered incidents
3. **Jaeger** → trace the remediation flow (detection → RCA → decision → remediation)
4. **Kibana** → filter logs by `incident.id` to see the full audit trail
5. **Kafka UI** → verify all pipeline topics processed the events correctly
