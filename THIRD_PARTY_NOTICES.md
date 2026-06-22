# Third-Party Notices

This prototype is MIT-licensed. It depends on the open-source packages below and adapts a small
number of public UI **patterns** (re-implemented against Forge System tokens — none vendored
verbatim). Resolved versions/licenses should be re-confirmed from lockfiles after install.

## Runtime dependencies

### Backend (Python) — all permissive
FastAPI (MIT) · Starlette (BSD-3) · Uvicorn (BSD-3) · SQLModel (MIT) · SQLAlchemy (MIT) ·
Pydantic / pydantic-core (MIT) · NumPy (BSD-3) · httpx (BSD-3) · python-multipart (Apache-2.0) ·
*optional:* LangGraph / LangChain-core (MIT).

### Frontend (Node) — all permissive
Next.js (MIT) · React / React-DOM (MIT) · Tailwind CSS (MIT) · @tanstack/react-query (MIT) ·
Zod (MIT) · Framer Motion (MIT) · lucide-react (ISC) · Radix UI primitives (MIT) · cmdk (MIT).

## Dev dependencies
pytest (MIT) · ruff (MIT) · mypy (MIT) · Vitest (MIT) · Testing Library (MIT) ·
Playwright (Apache-2.0) · TypeScript (Apache-2.0) · ESLint (MIT).

## Adapted UI patterns
- **Command palette** — built on `cmdk` (MIT) + Radix Dialog; styling original.
- **Dialog / Tooltip / Popover / Tabs / Switch** — Radix primitives (MIT), Forge-themed.
- General dashboard-shell / timeline / data-card patterns were informed by publicly known product
  conventions (Linear, Vercel, Sentry, control-room UIs) at the level of *information architecture
  only*. No proprietary asset, illustration, layout, or copy was reproduced. See
  [`docs/FRONTEND_RESEARCH.md`](docs/FRONTEND_RESEARCH.md).

## Reference screenshots
The Efficast product screenshots (`*.webp`, `*.png`) in the repo root are third-party captures used
privately as design research only; they are not part of the application and should be removed before
public distribution. Trademarks/logos therein belong to their owners.

_If any component is later vendored from a specific source, its name, URL, license, and the
modifications made will be appended here._
