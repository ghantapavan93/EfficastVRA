"""Architecture fitness functions — the layering is *enforced*, not just documented.

These tests parse the import graph of ``app/`` and assert the hexagonal boundaries hold, so the
architecture can't silently erode (see docs/ARCHITECTURE.md and docs/adr/). They are the executable
counterpart of the ADRs.

Layers (driving adapters → application → ports → domain core):
  api / main / cli / synthetic   →  workflow / agent / services / gateway / reasoning / rag / integration
                                  →  ports (efficast_port, reasoning.base, telemetry)  →  domain
"""

from __future__ import annotations

import ast
import pathlib

import app

APP = pathlib.Path(app.__file__).resolve().parent
LAYERS = ["api", "workflow", "gateway", "agent", "services", "adapters", "rag", "reasoning",
          "integration", "tools", "seed"]


def _module_imports(pyfile: pathlib.Path) -> set[str]:
    tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                mods.add(n.name)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module)
    return mods


def _files(*subpkgs: str) -> list[pathlib.Path]:
    roots = [APP / s for s in subpkgs] if subpkgs else [APP]
    out: list[pathlib.Path] = []
    for r in roots:
        out.extend(p for p in r.rglob("*.py"))
    return out


def _imports_matching(prefixes: tuple[str, ...]) -> list:
    """(file, import) pairs where the file imports any of the given app.* prefixes."""
    hits = []
    for f in _files():
        rel = f.relative_to(APP).as_posix()
        for imp in _module_imports(f):
            if any(imp == p or imp.startswith(p + ".") for p in prefixes):
                hits.append((rel, imp))
    return hits


def test_domain_core_is_pure():
    """The domain core depends on nothing in the outer layers (it is the hexagon's center)."""
    forbidden = tuple(f"app.{lay}" for lay in LAYERS)
    bad = []
    for f in _files("domain"):
        for imp in _module_imports(f):
            if any(imp == p or imp.startswith(p + ".") for p in forbidden):
                bad.append((f.relative_to(APP).as_posix(), imp))
    assert bad == [], f"domain core must not import outer layers: {bad}"


def test_core_does_not_depend_on_the_web_layer():
    """Only *driving adapters* may import app.api — the API package, the entrypoint, and the MCP
    server (an alternative driving adapter). The core never depends on a delivery mechanism."""
    driving_adapters = ("api/", "main.py", "mcp_server.py")
    bad = [(rel, imp) for rel, imp in _imports_matching(("app.api",))
           if not any(rel == a or rel.startswith(a) for a in driving_adapters)]
    assert bad == [], f"only driving adapters may import app.api: {bad}"


def test_agent_and_reasoning_never_actuate():
    """The agent proposes; it must NOT import the gateway (only the workflow routes side effects)."""
    bad = []
    for f in _files("agent", "reasoning"):
        for imp in _module_imports(f):
            if imp == "app.gateway" or imp.startswith("app.gateway."):
                bad.append((f.relative_to(APP).as_posix(), imp))
    assert bad == [], f"agent/reasoning must not import the gateway (no model-driven side effects): {bad}"


def test_tools_are_executed_only_through_the_gateway():
    """The operational tool registry may be imported only by the gateway (the single choke point)."""
    bad = [(rel, imp) for rel, imp in _imports_matching(("app.tools",))
           if not (rel.startswith("gateway/") or rel.startswith("tools/"))]
    assert bad == [], f"only the gateway may reach the tool registry: {bad}"


def test_no_machine_control_symbol_exists_anywhere():
    """Defence in depth: no function/route in the codebase even names a machine-control action."""
    forbidden = ["start_machine", "stop_machine", "restart_machine", "machine_start", "machine_stop",
                 "machine_restart", "write_plc", "set_setpoint", "bypass_alarm", "bypass_interlock",
                 "confirm_loto"]
    bad = []
    for f in _files():
        src = f.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in forbidden:
                bad.append((f.relative_to(APP).as_posix(), node.name))
    assert bad == [], f"no machine-control function may exist: {bad}"
