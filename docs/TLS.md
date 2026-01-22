# TLS Configuration for LLMOps SDK

**Version:** 0.1  
**Date:** 2026-01-22  
**Status:** Implemented

---

## Overview

This document describes TLS certificate handling for self-hosted Arize AX deployments that use HTTPS with self-signed certificates.

---

## Problem Statement

Self-hosted Arize AX deployments often use self-signed certificates for HTTPS. These certificates are not in system trust stores, so the SDK must be configured with the certificate file to verify the server's identity.

---

## Solution

The SDK supports a single TLS configuration option:

```yaml
arize:
  endpoint: https://arize-app.your-cluster.internal/v1/traces
  certificate_file: ./certs/arize-ca.pem  # Path to CA certificate
```

### Path Resolution

- **Relative paths** are resolved from the config file's directory
- **Absolute paths** are used as-is
- **Environment variable fallback**: `OTEL_EXPORTER_OTLP_CERTIFICATE`

---

## User Workflow

### Step 1: Extract Certificate (One-Time Setup)

Extract the server certificate from your Arize endpoint:

```bash
mkdir -p ./certs
echo | openssl s_client -showcerts -connect arize-app.your-cluster.internal:443 -prexit > ./certs/arize-ca.pem
```

### Step 2: Configure SDK

Reference the certificate in your `llmops.yaml`:

```yaml
service:
  name: my-service

arize:
  endpoint: https://arize-app.your-cluster.internal/v1/traces
  space_id: ${ARIZE_SPACE_ID}
  api_key: ${ARIZE_API_KEY}
  project_name: my-project
  certificate_file: ./certs/arize-ca.pem

validation:
  mode: strict  # Fail if certificate file not found
```

### Step 3: Initialize SDK

```python
import llmops

llmops.instrument(config_path="./llmops.yaml")
```

---

## How It Works

1. **Config loading**: SDK reads `certificate_file` from config (or `OTEL_EXPORTER_OTLP_CERTIFICATE` env var)
2. **Path resolution**: Relative paths are resolved from the config file's directory
3. **Validation**: In strict mode, SDK verifies the file exists at startup
4. **Environment bridging**: SDK sets `OTEL_EXPORTER_OTLP_CERTIFICATE` env var so `arize.otel.register()` can use it
5. **HTTPS connection**: OpenTelemetry exporter uses the certificate to verify the server

---

## Understanding Your Certificate

### Check What Type of Certificate Your Endpoint Uses

```bash
echo | openssl s_client -connect arize-app.your-cluster.internal:443 2>/dev/null | openssl x509 -noout -issuer -subject
```

**Output interpretation:**

| Subject | Issuer | Type | certificate_file needed? |
|---------|--------|------|--------------------------|
| Same as issuer | Same as subject | Self-signed | **Yes** |
| Your domain | Company CA | Enterprise PKI | Maybe (if CA not in trust store) |
| Your domain | Let's Encrypt / DigiCert / etc. | Public CA | No |

### Check Verify Status

```bash
echo | openssl s_client -connect arize-app.your-cluster.internal:443 2>/dev/null | grep "Verify return code"
```

| Code | Meaning | Action |
|------|---------|--------|
| `0 (ok)` | Certificate trusted | No `certificate_file` needed |
| `18 (self-signed certificate)` | Self-signed | **Need `certificate_file`** |
| `19 (self-signed certificate in chain)` | Self-signed CA | **Need `certificate_file`** |
| `20 (unable to get local issuer certificate)` | CA not trusted | **Need `certificate_file`** |

---

## TLS Maturity Progression

As deployments mature, TLS handling evolves:

### Development: Self-Signed Certificate

```yaml
arize:
  endpoint: https://arize.dev.internal/v1/traces
  certificate_file: ./certs/arize-ca.pem
```

- Manual certificate extraction required
- Certificate file checked into project or mounted as secret

### Production: Enterprise CA or Public CA

```yaml
arize:
  endpoint: https://arize.company.com/v1/traces
  # No certificate_file needed if CA is in system trust store
```

- IT/Security manages certificates
- CA trusted system-wide

### Production: Kubernetes with cert-manager

```yaml
arize:
  endpoint: https://arize.company.com/v1/traces
  # No certificate_file needed - cert-manager + Let's Encrypt
```

- Automatic certificate provisioning and renewal
- Public CA trusted by all clients

### Production: Service Mesh (Istio/Linkerd)

```yaml
arize:
  endpoint: http://arize.namespace.svc.cluster.local/v1/traces
  # No TLS config - mesh handles encryption transparently
```

- Zero TLS configuration in application
- Mesh manages mTLS between services

---

## Troubleshooting

### Certificate file not found

```
ConfigurationError: Certificate file not found: ./certs/arize-ca.pem
```

**Solution**: Ensure the file exists at the specified path relative to your config file.

### SSL certificate verify failed

```
ssl.SSLCertVerificationError: certificate verify failed
```

**Solution**: The certificate file may be incorrect or outdated. Re-extract it:

```bash
echo | openssl s_client -showcerts -connect <host>:443 -prexit > ./certs/arize-ca.pem
```

### Connection refused or timeout

**Solution**: Verify the endpoint is correct and reachable:

```bash
curl -v --cacert ./certs/arize-ca.pem https://arize-app.your-cluster.internal/health
```

---

## Design Decisions

### Why Only `certificate_file`?

The SDK originally supported mTLS (mutual TLS) with `client_key_file` and `client_certificate_file`. These were removed because:

1. **Arize doesn't require mTLS** - API key authentication is sufficient
2. **Simpler configuration** - One field instead of three
3. **Reduced confusion** - Users only need to understand one concept

Users with advanced mTLS requirements can set the standard OTEL environment variables directly.

### Why Relative Path Resolution?

Relative paths resolve from the config file's directory because:

1. **Predictable** - Same behavior regardless of working directory
2. **Portable** - Config and certs can be co-located and moved together
3. **Intuitive** - `./certs/ca.pem` means "certs folder next to this config file"

---

**Document Owner:** Platform Team  
**Last Updated:** 2026-01-22
