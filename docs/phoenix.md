# Phoenix Trace Backend Plan

This document describes the planned production trace architecture:

```text
AgentScope App
  -> OpenTelemetry Collector
     -> Phoenix
        -> PostgreSQL
```

The goal is to avoid using AgentScope Studio's local SQLite store as the long-term trace backend. Studio can remain useful for local debugging, but production trace storage should be handled by a backend designed for OpenTelemetry traffic, retention, and database persistence.

## Architecture

### Components

- AgentScope App emits trace data through OTLP by setting `tracing_url`.
- OpenTelemetry Collector receives application traces, batches them, applies memory limits and sampling, and forwards them to Phoenix.
- Phoenix receives OTLP traces, provides the trace UI, and persists data in PostgreSQL.
- PostgreSQL stores Phoenix data on persistent volumes and is managed independently from application pods.

### Traffic Flow

```text
AgentScope workload
  -> http://otel-collector:4318/v1/traces
  -> OpenTelemetry Collector traces pipeline
  -> http://phoenix:6006/v1/traces
  -> Phoenix
  -> PostgreSQL
```

Use the Collector as the stable ingestion endpoint instead of sending every application directly to Phoenix. This keeps sampling, batching, retries, and future fan-out outside application code.

## AgentScope Configuration

Configure applications to send traces to the OpenTelemetry Collector:

```python
import agentscope

agentscope.init(
    tracing_url="http://otel-collector:4318/v1/traces",
)
```

For local validation without the Collector, traces can be sent directly to Phoenix:

```python
agentscope.init(
    tracing_url="http://phoenix:6006/v1/traces",
)
```

For Phoenix Cloud, pass the API key through OTLP headers:

```python
import os
import agentscope

os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = (
    f"api_key={os.environ['PHOENIX_API_KEY']}"
)

agentscope.init(
    tracing_url="https://app.phoenix.arize.com/v1/traces",
)
```

## Phoenix Deployment

Phoenix should run as a K8s Deployment backed by PostgreSQL. SQLite is suitable for local development, but PostgreSQL is the safer production choice because pod restarts and rescheduling should not affect trace persistence.

Recommended Phoenix environment variables:

```yaml
env:
  - name: PHOENIX_SQL_DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: phoenix-db
        key: database-url
  - name: PHOENIX_DEFAULT_RETENTION_POLICY_DAYS
    value: "30"
```

Example `database-url` secret value:

```text
postgresql://phoenix:password@postgres:5432/phoenix
```

Expose Phoenix internally:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: phoenix
spec:
  selector:
    app: phoenix
  ports:
    - name: http
      port: 6006
      targetPort: 6006
    - name: otlp-grpc
      port: 4317
      targetPort: 4317
```

The UI can be exposed through an internal Ingress. Avoid exposing OTLP ingestion publicly unless authentication, rate limits, and network policies are in place.

## Collector Deployment

Run the Collector as the ingestion layer for application traces. Start with a gateway Deployment; add DaemonSet agents later if node-local collection is required.

Baseline Collector configuration:

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128
  batch:
    timeout: 5s
    send_batch_size: 1024
  tail_sampling:
    decision_wait: 10s
    num_traces: 50000
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes:
            - ERROR
      - name: slow-traces
        type: latency
        latency:
          threshold_ms: 3000
      - name: baseline-sampling
        type: probabilistic
        probabilistic:
          sampling_percentage: 10

exporters:
  otlphttp/phoenix:
    endpoint: http://phoenix:6006

service:
  pipelines:
    traces:
      receivers:
        - otlp
      processors:
        - memory_limiter
        - tail_sampling
        - batch
      exporters:
        - otlphttp/phoenix
```

For Phoenix Cloud, add headers to the exporter:

```yaml
exporters:
  otlphttp/phoenix:
    endpoint: https://app.phoenix.arize.com
    headers:
      api_key: ${env:PHOENIX_API_KEY}
```

## Storage And Retention

Use PostgreSQL persistent storage for Phoenix. The minimum production setup should include:

- PersistentVolumeClaim for PostgreSQL data.
- Automated database backups.
- Retention policy for old traces.
- Monitoring on database size, write latency, slow queries, CPU, memory, and disk pressure.
- A documented restore procedure tested outside production.

Start with 30 days of retention unless the business requirement demands more. Increase retention only after measuring write volume and query cost.

## Sampling Strategy

Trace volume can grow quickly. Do not send every successful trace forever.

Recommended initial policy:

- Keep error traces at 100%.
- Keep slow traces at 100%.
- Sample ordinary successful traces at 5% to 10%.
- Allow temporary high-sampling windows for specific environments, tenants, or run IDs.
- Keep development and staging sampling higher than production if debugging velocity matters.

If exact business audits are required, do not rely on sampled traces as the source of truth. Store audit records separately in the application domain database.

## Optional Studio Fan-Out

AgentScope Studio can still be used for local debugging or low-volume visual inspection. If both Phoenix and Studio are needed, do fan-out in the Collector:

```text
AgentScope App
  -> OpenTelemetry Collector
     -> Phoenix
     -> AgentScope Studio
```

Only send sampled or development traffic to Studio. Do not use Studio SQLite as the full production trace store.

## Rollout Plan

1. Validate locally with `AgentScope App -> Phoenix`.
2. Deploy Phoenix with PostgreSQL in a test K8s namespace.
3. Deploy OpenTelemetry Collector and point a test AgentScope workload at `http://otel-collector:4318/v1/traces`.
4. Verify trace visibility in Phoenix and check that PostgreSQL persists data across Phoenix pod restarts.
5. Add memory limiter, batch, and sampling processors.
6. Load test expected trace volume and tune batch sizes, sampling percentage, and PostgreSQL resources.
7. Add backups, retention, alerts, and dashboards.
8. Move production AgentScope workloads to the Collector endpoint.
9. Keep Studio as an optional sampled/debug sink only if needed.

## Open Questions

- Which Phoenix deployment mode will be used: self-hosted or Phoenix Cloud?
- What retention period is required by product and compliance?
- What trace volume is expected per day after sampling?
- Should sampling rules depend on tenant, environment, model, run ID, or error type?
- Does Phoenix display AgentScope span attributes well enough, or do we need Collector attribute transforms?

## References

- AgentScope Observability: https://docs.agentscope.io/observe-and-evaluate/observability
- Phoenix configuration: https://arize.com/docs/phoenix/deployment/configuration
- Phoenix self-hosting architecture: https://arize.com/docs/phoenix/self-hosting/architecture
- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
- OpenTelemetry sampling: https://opentelemetry.io/docs/concepts/sampling/
