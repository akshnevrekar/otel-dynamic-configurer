# otel-dynamic-configurer

A sidecar container design for dynamically updating OpenTelemetry Collector configurations at runtime without restarting the pods.

---

## Architecture Overview

This project consists of an OpenTelemetry Collector deployment running with process namespace sharing (`shareProcessNamespace: true`) and two helper containers:

1. **Init Container (`otel-init-configurer`)**:
   - Seeds the dynamic configuration file in a shared Persistent Volume Claim (PVC) if it does not already exist.
   - Validates the existing merged configuration using `otelcol-contrib validate` at startup. If validation fails, it falls back to a safe, default configuration to ensure the pod boots up successfully.

2. **Sidecar Container (`otel-dynamic-configurer`)**:
   - Exposes a FastAPI-based REST API on port `8000`.
   - Listens for configuration updates via `POST /otel/config` as raw YAML.
   - Automatically validates the new configuration using `otelcol-contrib validate` before writing it.
   - Overwrites the configuration file on the PVC and sends a `SIGHUP` signal to the `otelcol-contrib` process to trigger a hot reload without pod termination.

```
+---------------------------------------------------------------+
| Pod                                                           |
|                                                               |
|  +---------------------+         +-------------------------+  |
|  |                     |  SIGHUP |                         |  |
|  | otel-collector      |<--------| otel-dynamic-configurer |  |
|  | (otelcol-contrib)   |         | (FastAPI Sidecar)       |  |
|  +----------+----------+         +------------+------------+  |
|             |                                 |               |
|             v Reads                           v Writes        |
|  +---------------------------------------------------------+  |
|  |                PVC (dynamic-config.yaml)                |  |
|  +---------------------------------------------------------+  |
+---------------------------------------------------------------+
```

---

## API Reference

### `POST /otel/config`

Updates the dynamic configuration of the OpenTelemetry Collector.

- **Request Headers**:
  - `Content-Type: application/yaml` or `text/yaml`
- **Request Body**:
  - Raw YAML representing the dynamic part of the OpenTelemetry Collector configuration.

#### Response Statuses
- **`200 OK` (Config Updated)**:
  ```json
  {
    "status": "updated",
    "file": "/pvc-config-storage/dynamic-config.yaml",
    "signal_sent_to_pid": 1234
  }
  ```
- **`200 OK` (No Change)**:
  ```json
  {
    "status": "no-change",
    "file": "/pvc-config-storage/dynamic-config.yaml"
  }
  ```
- **`400 Bad Request` (Validation Failed / Invalid YAML)**:
  ```json
  {
    "detail": "Config validation failed:\nError: ..."
  }
  ```

---

## Testing & Verification

### 1. Access the API
Port-forward the `otel-collector` service to access the configurer API on your local machine:
```bash
kubectl port-forward svc/otel-collector 8000:8000
```

### 2. Apply a Valid Config
Send a new valid dynamic configuration (e.g., enabling the OTLP receiver and updating the metrics pipeline):
```bash
curl -X POST http://localhost:8000/otel/config \
  -H "Content-Type: application/yaml" \
  --data-binary '
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: "0.0.0.0:4317"
      http:
        endpoint: "0.0.0.0:4318"
service:
  pipelines:
    metrics:
      receivers: [nop, otlp]
      processors: [batch]
      exporters: [debug]
'
```

### 3. Test Invalid Configuration Validation
Verify that invalid configuration updates are safely rejected:
```bash
curl -X POST http://localhost:8000/otel/config \
  -H "Content-Type: application/yaml" \
  --data-binary '
service:
  pipelines:
    metrics:
      receivers: [non-existent-receiver]
      processors: [batch]
      exporters: [debug]
'
```
*(Returns a `400 Bad Request` error with validation output)*

---

## Development

Build and push the docker image:
```bash
cd otel-dynamic-configurer
make publish
```
