"""Emit the contract v0.1 as JSON Schema files + a sample replay bundle.

Run: ``python -m app.integration.efficast.export_schemas``  → writes to
``<repo>/schemas/efficast-recovery-v0.1/`` (the Pydantic models in contract.py are the source of truth).
"""

from __future__ import annotations

import json
import pathlib

from app.integration.efficast.contract import CONTRACT_VERSION, EVENT_MODELS, EfficastEvent
from app.integration.efficast.fixtures import make_f27_bundle

_OUT = pathlib.Path(__file__).resolve().parents[4] / "schemas" / f"efficast-recovery-v{CONTRACT_VERSION}"


def export() -> pathlib.Path:
    _OUT.mkdir(parents=True, exist_ok=True)
    # envelope (base) + per-event schemas
    (_OUT / "envelope.schema.json").write_text(
        json.dumps(EfficastEvent.model_json_schema(), indent=2), encoding="utf-8")
    for event_type, model in sorted(EVENT_MODELS.items()):
        (_OUT / f"{event_type}.schema.json").write_text(
            json.dumps(model.model_json_schema(), indent=2), encoding="utf-8")
    # index
    (_OUT / "index.json").write_text(json.dumps({
        "contract_version": CONTRACT_VERSION,
        "envelope": "envelope.schema.json",
        "events": sorted(EVENT_MODELS.keys()),
    }, indent=2), encoding="utf-8")
    # sample bundle (sanitised F27 scenario, recovered)
    with (_OUT / "sample-bundle.jsonl").open("w", encoding="utf-8") as fh:
        for ev in make_f27_bundle(cycles=30):
            fh.write(json.dumps(ev.model_dump(mode="json")) + "\n")
    return _OUT


if __name__ == "__main__":
    out = export()
    print(f"wrote contract v{CONTRACT_VERSION} schemas + sample bundle to {out}")
