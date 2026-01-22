# PRD_01 — Conceptual Architecture

**Version:** 0.1
**Date:** 2026-01-21
**Status:** Draft

---

## 1. Overview

This document describes the high-level shape of the PRD_01 system. It focuses on concepts and relationships, not implementation details. The system provides a single-call setup for Arize telemetry in greenfield GenAI applications.

---

## 2. Core Concept

A single initialization call wires three concerns:
- Configuration loading from an explicit `llmops.yaml`/`llmops.yml` path
- Arize telemetry setup via OpenTelemetry
- Auto-instrumentation for Google ADK and Google GenAI

```
┌──────────────────────────────────────────────────────────────────────┐
│                         APPLICATION CODE                              │
│                                                                      │
│  import llmops                                                       │
│  llmops.instrument()  ────────────────────────────────────────────┐  │
│                                                                  │  │
│  # Google ADK + Google GenAI calls are auto-traced                │  │
│                                                                  │  │
└──────────────────────────────────────────────────────────────────────┘
                                                                  │
                                                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         LLMOPS SDK                                   │
│                                                                      │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────────────┐  │
│  │ Config Loader│──▶│ Arize Telemetry  │──▶│ Instrumentor Runner  │  │
│  │ (path+env)   │   │ (OTel provider)  │   │ (ADK + GenAI)         │  │
│  └──────────────┘   └──────────────────┘   └──────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                                                  │
                                                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         ARIZE BACKEND                                │
│                                                                      │
│  Phoenix / Arize AX receives GenAI spans                              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Primary Flow (Auto-Instrumentation)

```
Application startup
        │
        ▼
  llmops.instrument()
        │
        ▼
  Load config (explicit path via init or env var)
        │
        ▼
  Initialize Arize telemetry (TracerProvider + exporter)
        │
        ▼
  Instrument Google ADK + Google GenAI
        │
        ▼
  GenAI spans exported to Arize
```

---

## 4. Configuration Flow

```
┌──────────────────┐     ┌─────────────────────────┐
│ config path arg  │────▶│ Config Loader           │
└──────────────────┘     │ - validates fields      │
                         │ - applies defaults      │
┌──────────────────┐     │ - merges env overrides  │
│ LLMOPS_CONFIG    │────▶│                         │
└──────────────────┘     └─────────────┬──────────┘
                                      │
                                      ▼
                            ┌─────────────────────┐
                            │ Init Configuration  │
                            └─────────────────────┘
```

---

## 5. Key Invariants

- Telemetry never breaks business logic.
- `instrument()` is a single synchronous call.
- Only single-backend greenfield setups are supported.
- All configuration is file-first with explicit path selection.
- Config validation supports strict and permissive modes.

---

## 6. Separation of Responsibilities

- **Application code**: calls `instrument()` and runs business logic.
- **Config loader**: resolves file + env settings into a validated config.
- **Telemetry setup**: creates the tracer provider and exporter for Arize.
- **Instrumentor runner**: wires Google ADK + Google GenAI auto-instrumentation.

---

## 7. Extension Points (Conceptual)

```
Instrumentor Registry
├── Google ADK (enabled by default)
├── Google GenAI (enabled by default)
└── OpenAI (future)
```

The registry is a conceptual map of supported instrumentors; the public API does not change when new instrumentors are added.

---

## 8. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/PRD_01.md` | Requirements and success criteria |
| Reference Architecture (next) | Architectural patterns and invariants |
| API Specification (next) | Public interfaces and configuration contracts |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-21
