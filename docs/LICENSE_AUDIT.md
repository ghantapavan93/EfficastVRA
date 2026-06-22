# License Audit

**Prototype license:** MIT (see [`/LICENSE`](../LICENSE)).

All selected dependencies are permissive (MIT / BSD / Apache-2.0 / ISC / PostgreSQL). No copyleft
(GPL/AGPL) runtime dependency is introduced. Versions are pinned in `backend/pyproject.toml` and
`frontend/package.json`; exact resolved versions/licenses should be re-confirmed from lockfiles
after `pip install` / `npm install` (Phase 7) — see [`RESEARCH_GAPS.md`](RESEARCH_GAPS.md).

## Backend (Python)

| Package | Expected license | Use |
|---|---|---|
| fastapi | MIT | HTTP API |
| uvicorn | BSD-3-Clause | ASGI server |
| sqlmodel | MIT | ORM + Pydantic models |
| SQLAlchemy | MIT | (transitive) engine |
| pydantic / pydantic-core | MIT | validation |
| numpy | BSD-3-Clause | cosine retrieval |
| httpx | BSD-3-Clause | optional hosted reasoning |
| python-multipart | Apache-2.0 | file/evidence upload |
| pytest | MIT | tests (dev) |
| ruff | MIT | lint (dev) |
| langgraph *(optional)* | MIT | agent flow seam (not required at runtime) — see caveat below |

> ⚠️ **LangGraph transitive-license caveat (verified 2026-06-21):** the `langgraph` and
> `langchain-core` *libraries* are MIT, but the **`langgraph-api` server runtime** used by
> `langgraph dev` / `langgraph build` is **Elastic License 2.0** (commercial key required in
> production). This prototype makes LangGraph **optional** and ships a `DeterministicReasoningProvider`
> that carries the full demo, so **no Elastic-licensed component (`langgraph-api`) is used or required**.
> If a hosted LangGraph flow is added later, it must use the MIT libraries directly (not the
> `langgraph-api` server) to stay permissive. See [`RESEARCH_GAPS.md`](RESEARCH_GAPS.md).

## Frontend (Node)

| Package | Expected license | Use |
|---|---|---|
| next | MIT | framework |
| react / react-dom | MIT | UI runtime |
| typescript | Apache-2.0 | types (dev) |
| tailwindcss | MIT | styling |
| @tanstack/react-query | MIT | data layer |
| zod | MIT | client schema validation |
| framer-motion | MIT | motion (single animation lib) |
| lucide-react | ISC | icons |
| @radix-ui/* | MIT | accessible primitives |
| cmdk | MIT | command palette |
| vitest / @testing-library/* / @playwright/test | MIT | tests (dev) |

## Adapted third-party UI

Any component pattern adapted from a public source (shadcn/ui, Radix examples, 21st.dev, etc.) is
**re-implemented against Forge System tokens**, not copied verbatim, and is recorded in
[`/THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). At the time of writing, UI is built on Radix
primitives + custom components; no proprietary or non-permissive component is vendored.

## Reference screenshots

The `*.webp` / `*.png` Efficast screenshots in the repo root are **third-party product captures**
used only as private design research. They are **not** redistributed in the application, are
git-ignored from any build output, and should be removed before any public distribution of this
repo. Logos/marks visible in them belong to their respective owners.
