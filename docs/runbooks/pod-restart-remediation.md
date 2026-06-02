# Runbook: Pod Restart Remediation
* Target: Failing, crash-looping, or unresponsive pods.
* Trigger: CPU spike or 5xx error rate increase linked to container deadlock.
* Action: Execute Kubernetes API delete pod command.