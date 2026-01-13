# Backend Infrastructure Setup

Local Phoenix and MLflow backends for LLM observability.

## Prerequisites

- Docker Desktop for Mac (M2 compatible)
- Docker Compose (included with Docker Desktop)

## Quick Start

```bash
# Start both backends
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop backends
docker-compose down

# Stop and remove volumes (reset all data)
docker-compose down -v
```

## Access URLs

- **Phoenix UI:** http://localhost:6006
- **MLflow UI:** http://localhost:5001 (Note: Changed from default 5000 due to macOS AirPlay conflict)

## Backend Details

### Phoenix (Port 6006)

- **Purpose:** Real-time trace visualization with OpenInference
- **OTLP Endpoint:** `http://localhost:6006/v1/traces`
- **Health Check:** `http://localhost:6006/healthz`
- **Data Storage:** Docker volume `phoenix-data`

### MLflow (Port 5001)

- **Purpose:** ML experiment tracking with OTLP ingestion
- **OTLP Endpoint:** `http://localhost:5001/v1/traces`
- **Health Check:** `http://localhost:5001/health`
- **Data Storage:** Docker volume `mlflow-data` (SQLite backend)
- **Note:** External port is 5001 (macOS uses 5000 for AirPlay Receiver)

## Validation

```bash
# Check backend health
curl http://localhost:6006/healthz
curl http://localhost:5001/health

# Run validation script
cd ..
python scripts/validate_backends.py
```

## Troubleshooting

### Ports already in use

```bash
# Check what's using port 6006 or 5000
lsof -i :6006
lsof -i :5000

# Stop conflicting services or change ports in docker-compose.yaml
```

### Container won't start

```bash
# View detailed logs
docker-compose logs phoenix
docker-compose logs mlflow

# Restart a specific service
docker-compose restart phoenix
```

### Reset everything

```bash
# Stop, remove containers, and delete all data
docker-compose down -v

# Pull fresh images
docker-compose pull

# Start fresh
docker-compose up -d
```

## M2 MacBook Notes

- Both images support ARM64 architecture (linux/arm64)
- No Rosetta emulation needed
- Native performance on Apple Silicon
