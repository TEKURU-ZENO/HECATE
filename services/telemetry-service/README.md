# telemetry-service
FastAPI service that accepts telemetry pushes (metrics, logs) and publishes to Kafka.

## Endpoints
* `/health` — GET status
* `/api/v1/...` — Service logic routes