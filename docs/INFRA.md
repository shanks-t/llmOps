# Infrastructure Setup - LLM Observability Backends

**Version:** v0.1 (PoC Phase)
**Last Updated:** 2026-01-13
**Status:** ✅ Operational

---

## Overview

This document describes the local observability infrastructure for the LLM Observability SDK proof of concept. Two backend services run locally via Docker Compose to receive and visualize telemetry data from ADK applications.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  ADK Application (with SDK)                                 │
│  - Agent workflows                                           │
│  - LLM calls                                                 │
│  - Tool executions                                           │
└─────────────────────────────────────────────────────────────┘
                    ↓
            OTLP Traces (HTTP)
                    ↓
    ┌───────────────┴────────────────┐
    ↓                                 ↓
┌──────────────────┐        ┌──────────────────┐
│  Phoenix         │        │  MLflow          │
│  localhost:6006  │        │  localhost:5001  │
│  (OpenInference) │        │  (OTLP)          │
└──────────────────┘        └──────────────────┘
```

---

## Prerequisites

### Required Software

- **Docker Desktop for Mac** (M2 compatible)
  - Includes Docker Compose
  - Download: https://www.docker.com/products/docker-desktop

- **UV** (Python package manager)
  - For running validation scripts
  - Install: `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`

### System Requirements

- **Platform:** macOS (M2 MacBook / Apple Silicon)
- **Architecture:** ARM64 (linux/arm64 containers)
- **Disk Space:** ~2GB for Docker images + volumes
- **Available Ports:** 6006 (Phoenix), 5001 (MLflow)

---

## Backend Services

### Phoenix (Arize)

**Purpose:** Real-time trace visualization with OpenInference semantic conventions

**Details:**
- **UI:** http://localhost:6006
- **OTLP Endpoint:** `http://localhost:6006/v1/traces`
- **Health Check:** `http://localhost:6006/healthz`
- **Protocol:** HTTP (OTLP)
- **Container:** `docker-phoenix-1`
- **Image:** `arizephoenix/phoenix:latest`
- **Storage:** Docker volume `phoenix-data`
- **Database:** SQLite (`/data/phoenix.db` inside container)

**Features:**
- Native Google ADK instrumentation support
- OpenInference semantic conventions
- Real-time trace visualization
- Span search and filtering
- Token usage tracking
- No authentication required (local dev)

---

### MLflow

**Purpose:** ML experiment tracking with OTLP trace ingestion

**Details:**
- **UI:** http://localhost:5001
- **OTLP Endpoint:** `http://localhost:5001/v1/traces`
- **Health Check:** `http://localhost:5001/health`
- **Protocol:** HTTP (OTLP)
- **Container:** `docker-mlflow-1`
- **Image:** `ghcr.io/mlflow/mlflow:latest`
- **Storage:** Docker volume `mlflow-data`
- **Database:** SQLite (`/mlflow/mlflow.db` inside container)

**Important Notes:**
- ⚠️ **External port is 5001** (not default 5000)
- **Reason:** macOS uses port 5000 for AirPlay Receiver
- Internal container port remains 5000 (mapped to 5001)
- MLflow requires SQL backend for OTLP ingestion (file-based stores not supported)

**Features:**
- OTLP trace ingestion (via `/v1/traces`)
- Experiment and run tracking
- Artifact storage
- Metrics and parameters logging
- Localhost-only security by default

---

## Quick Start

### 1. Start Backends

```bash
cd docker
docker-compose up -d
```

**Expected output:**
```
✔ Container docker-phoenix-1  Started
✔ Container docker-mlflow-1   Started
```

### 2. Verify Status

```bash
# Check running containers
docker-compose ps

# Validate backends
cd ..
uv run python scripts/validate_backends.py
```

**Expected validation output:**
```
✅ Phoenix is healthy: http://localhost:6006/healthz
✅ Phoenix OTLP endpoint is accessible
✅ MLflow is healthy: http://localhost:5001/health
✅ MLflow OTLP endpoint is accessible
```

### 3. Access UIs

**Phoenix:**
```bash
open http://localhost:6006
```

**MLflow:**
```bash
open http://localhost:5001
```

---

## Common Commands

### Starting & Stopping

```bash
# Start backends
cd docker && docker-compose up -d

# Stop backends (preserves data)
cd docker && docker-compose down

# Stop and remove all data (DESTRUCTIVE)
cd docker && docker-compose down -v
```

### Monitoring

```bash
# View all logs (follow mode)
cd docker && docker-compose logs -f

# View Phoenix logs only
cd docker && docker-compose logs -f phoenix

# View MLflow logs only
cd docker && docker-compose logs -f mlflow

# Check container status
cd docker && docker-compose ps
```

### Maintenance

```bash
# Restart specific service
cd docker && docker-compose restart phoenix
cd docker && docker-compose restart mlflow

# Restart all services
cd docker && docker-compose restart

# Pull latest images
cd docker && docker-compose pull

# Rebuild containers
cd docker && docker-compose up -d --build
```

### Data Management

```bash
# View volumes
docker volume ls | grep docker

# Inspect Phoenix data
docker volume inspect docker_phoenix-data

# Inspect MLflow data
docker volume inspect docker_mlflow-data

# Backup Phoenix data (example)
docker run --rm -v docker_phoenix-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/phoenix-backup.tar.gz /data

# Reset everything (DESTRUCTIVE)
cd docker && docker-compose down -v
```

---

## Validation

### Automated Validation Script

```bash
uv run python scripts/validate_backends.py
```

**Checks performed:**
1. Docker containers are running
2. Phoenix health endpoint responds
3. Phoenix OTLP endpoint is accessible
4. MLflow health endpoint responds
5. MLflow OTLP endpoint is accessible

### Manual Health Checks

```bash
# Phoenix health
curl http://localhost:6006/healthz
# Expected: 200 OK

# MLflow health
curl http://localhost:5001/health
# Expected: 200 OK
```

### Test OTLP Connectivity

```bash
# Phoenix OTLP endpoint (will return 415 without proper headers - this is OK)
curl -X POST http://localhost:6006/v1/traces

# MLflow OTLP endpoint (will return 422 without payload - this is OK)
curl -X POST http://localhost:5001/v1/traces
```

**Note:** Error responses (415, 422) indicate the endpoints are listening but require proper OTLP payloads. This is expected behavior.

---

## Troubleshooting

### Port Conflicts

**Problem:** `bind: address already in use`

**Solution for MLflow (port 5001):**
```bash
# Check what's using the port
lsof -i :5001

# If conflict, change port in docker-compose.yaml
ports:
  - "5002:5000"  # Use different external port
```

**Solution for Phoenix (port 6006):**
```bash
# Check what's using the port
lsof -i :6006

# If conflict, change port in docker-compose.yaml
ports:
  - "6007:6006"  # Use different external port
```

**macOS AirPlay Note:** Port 5000 is used by AirPlay Receiver (Control Center). We use 5001 for MLflow to avoid this conflict. To disable AirPlay Receiver:
```
System Settings → General → AirDrop & Handoff → AirPlay Receiver → Off
```

---

### Container Won't Start

**Problem:** Container exits immediately

**Debug steps:**
```bash
# View detailed logs
cd docker && docker-compose logs phoenix
cd docker && docker-compose logs mlflow

# Check Docker daemon
docker ps -a

# Remove and recreate containers
cd docker && docker-compose down
cd docker && docker-compose up -d
```

**Common issues:**
- Insufficient Docker resources (increase in Docker Desktop preferences)
- Corrupted volume data (try `docker-compose down -v` to reset)
- Port conflicts (see above)

---

### Unhealthy Container Status

**Problem:** `docker-compose ps` shows "unhealthy"

**Explanation:** Health check configuration may be too strict. If validation script passes, the services are working correctly.

**Verify manually:**
```bash
curl http://localhost:6006/healthz  # Should return 200
curl http://localhost:5001/health   # Should return 200
```

If both respond with 200 OK, the services are healthy despite Docker status.

---

### Docker Disk Space Issues

**Problem:** `no space left on device`

**Solution:**
```bash
# Check Docker disk usage
docker system df

# Clean up unused resources (SAFE - won't delete active containers/volumes)
docker system prune -a

# Full cleanup including volumes (DESTRUCTIVE)
docker system prune -af --volumes
```

**Recommendation:** Keep at least 10GB free for Docker operations.

---

### Validation Script Issues

**Problem:** `requests library not installed`

**Solution:**
```bash
# Ensure UV environment is active
uv add requests

# Run script with UV
uv run python scripts/validate_backends.py
```

**Problem:** Python version mismatch

**Solution:**
```bash
# Check Python version
python3 --version

# Recreate UV environment if needed
rm -rf .venv
uv venv
uv add requests
```

---

## Configuration Files

### Docker Compose

**Location:** `docker/docker-compose.yaml`

**Key settings:**
```yaml
services:
  phoenix:
    image: arizephoenix/phoenix:latest
    platform: linux/arm64  # M2 MacBook
    ports:
      - "6006:6006"
    volumes:
      - phoenix-data:/data

  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    platform: linux/arm64  # M2 MacBook
    ports:
      - "5001:5000"  # External:Internal
    volumes:
      - mlflow-data:/mlflow
```

### Validation Script

**Location:** `scripts/validate_backends.py`

**Endpoints checked:**
- Phoenix: `http://localhost:6006/healthz`
- Phoenix OTLP: `http://localhost:6006/v1/traces`
- MLflow: `http://localhost:5001/health`
- MLflow OTLP: `http://localhost:5001/v1/traces`

---

## Data Persistence

### Phoenix Data

- **Volume:** `docker_phoenix-data`
- **Path (container):** `/data/`
- **Database:** `/data/phoenix.db` (SQLite)
- **Retention:** Persists across container restarts
- **Reset:** `docker-compose down -v`

### MLflow Data

- **Volume:** `docker_mlflow-data`
- **Path (container):** `/mlflow/`
- **Database:** `/mlflow/mlflow.db` (SQLite)
- **Artifacts:** `/mlflow/artifacts/`
- **Retention:** Persists across container restarts
- **Reset:** `docker-compose down -v`

---

## Security Considerations

### Local Development Only

⚠️ **These configurations are for LOCAL DEVELOPMENT only:**
- No authentication enabled
- Ports exposed on all interfaces (0.0.0.0)
- Default security settings
- SQLite databases (not suitable for production)

### Production Deployment

For production use (out of scope for PoC):
- Enable authentication on both backends
- Use proper databases (PostgreSQL, MySQL)
- Configure TLS/SSL
- Restrict network access
- Deploy to separate infrastructure
- Implement access controls and audit logging

---

## Platform-Specific Notes

### M2 MacBook (Apple Silicon)

**Architecture:** ARM64 (linux/arm64)

**Advantages:**
- Native ARM64 images (no Rosetta emulation)
- Better performance and battery efficiency
- Full Docker support

**Platform configuration in docker-compose.yaml:**
```yaml
platform: linux/arm64
```

**Verified images:**
- `arizephoenix/phoenix:latest` - ARM64 native
- `ghcr.io/mlflow/mlflow:latest` - ARM64 native

---

## Next Steps

Once infrastructure is validated:

1. ✅ **Backends running** - Phoenix and MLflow operational
2. ⏭️ **Create SDK package structure** - `llm-observability/` package
3. ⏭️ **Implement config parser** - YAML configuration loading
4. ⏭️ **Implement adapters** - Phoenix and MLflow backend adapters
5. ⏭️ **Create example app** - ADK application with instrumentation
6. ⏭️ **Test telemetry flow** - End-to-end trace validation

---

## Reference Links

### Documentation

- **Phoenix:** https://arize.com/docs/phoenix
- **MLflow:** https://mlflow.org/docs/latest/
- **OTLP Specification:** https://opentelemetry.io/docs/specs/otlp/
- **Docker Compose:** https://docs.docker.com/compose/

### GitHub Repositories

- **Phoenix:** https://github.com/Arize-ai/phoenix
- **MLflow:** https://github.com/mlflow/mlflow
- **OpenInference:** https://github.com/Arize-ai/openinference

---

## Appendix: Backend Comparison

| Feature | Phoenix | MLflow |
|---------|---------|--------|
| **Primary Use Case** | LLM observability | ML experiment tracking |
| **OTLP Support** | Native | Via `/v1/traces` endpoint |
| **Semantic Conventions** | OpenInference | Generic OTLP |
| **ADK Integration** | GoogleADKInstrumentor | Manual OTLP setup |
| **UI Focus** | Trace visualization | Experiment comparison |
| **Storage** | SQLite (default) | SQLite (default) |
| **Authentication** | Optional | Optional |
| **Port** | 6006 | 5001 (5000 internally) |

---

**Infrastructure Status:** ✅ Ready for SDK Development

**Last Validated:** 2026-01-13 00:50 UTC
