# AGENTS.md

## Mandatory: Run Quality Checks After Every Code Change

**Before any code change is considered complete, run from `llm-observability-sdk/`:**

```bash
just
```

This runs all checks: Ruff (lint), MyPy (types), Bandit (security), and Pytest (tests).

**All checks must pass.** Do not skip or ignore failures.

| Command | Description |
|---------|-------------|
| `just` | Run all checks and tests (default) |
| `just lint` | Ruff linter only |
| `just typecheck` | MyPy type checker only |
| `just security` | Bandit security scanner only |
| `just test` | Pytest test suite only |
| `just lint-fix` | Auto-fix linting issues |
| `just format` | Auto-format code with Ruff |

---

## Project Context

This is a **proof of concept (POC)** to validate architecture, APIs, and developer experience—not a production-hardened system.

---

## Project Structure

| Path | Purpose |
|------|---------|
| `./docs/` | PRD, architecture, and API design documents |
| `./llm-observability-sdk/src/` | Implementation code |
| `./llm-observability-sdk/tests/` | Tests |
| `./llm-observability-sdk/examples/` | Usage examples |
| `INFRA.md` | Infrastructure details |

---

## Source of Truth

The **PRD** (in `./docs/`) is authoritative. All implementations must trace back to it.

If code conflicts with the PRD:
- Update the PRD first, **or**
- Revise the implementation

No silent divergence.

---

## Tooling

- **UV** is the required Python package manager
- **Just** is the task runner (see commands above)
- Keep lockfiles up to date

---

## Agent Rules

1. **Run `just` after every code change** (non-negotiable)
2. Read code before modifying it
3. Ask for clarification when requirements are ambiguous
4. Keep solutions simple—this is a POC
5. Propose changes explicitly, not implicitly
6. Update examples when code changes

---

## Do Not

- Skip quality checks
- Silently diverge from the PRD
- Over-engineer (no premature optimization)
- Add unnecessary abstractions
