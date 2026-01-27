# AGENTS.md

## Mandatory: Run Quality Checks After Every Code Change

**Before any code change is considered complete, run from `llm-observability-sdk/`:**

```bash
just
```
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
