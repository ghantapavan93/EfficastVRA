"""Connector catalog — how real plant data sources map onto this system's seams.

Mirrors the connector ecosystems of industrial-AI platforms (Cognite's ~100 extractors, Siemens
Xcelerator, UNS brokers — see docs/INDUSTRY_LANDSCAPE.md). Each connector is **declarative and
documented, not connected**: it states the protocol, direction, and which application seam
(`EfficastPort` / `EfficastApiPort` / `TelemetrySource`) it feeds — so a real deployment is a matter
of wiring a connector to a seam, not changing the application core. No connector can carry a
machine-control command; the system has no such seam.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConnectorSpec:
    key: str
    label: str
    protocol: str
    direction: str        # inbound | outbound | bidirectional
    feeds: str            # application seam it maps to
    description: str
    status: str = "reference"   # documented; the prototype runs on synthetic data


CONNECTORS: list[ConnectorSpec] = [
    ConnectorSpec(
        "opc_ua", "OPC-UA server", "OPC-UA", "inbound",
        "TelemetrySource + EfficastPort.get_machine_snapshot",
        "Subscribe to PLC/controller tags; map node-ids to machine signals (vibration, temperature, …)."),
    ConnectorSpec(
        "mqtt_uns", "Unified Namespace (MQTT / Sparkplug B)", "MQTT Sparkplug B", "bidirectional",
        "TelemetrySource (in) · EfficastPort.publish_* (out)",
        "Subscribe to ISA-95 UNS topics for live metrics; publish agent events/decisions back to the namespace."),
    ConnectorSpec(
        "mes_rest", "MES REST API (e.g. Efficast)", "HTTPS / REST", "bidirectional",
        "EfficastApiPort",
        "Production orders, OEE, quality, lots, and MAIA alerts; map JSON to the port DTOs."),
    ConnectorSpec(
        "pi_historian", "Process historian (OSIsoft PI / AVEVA)", "PI Web API / extractor", "inbound",
        "TelemetrySource (live + historical backfill)",
        "Stream and backfill time-series so verification windows can replay real post-intervention cycles."),
    ConnectorSpec(
        "cmms_erp", "CMMS / ERP", "HTTPS / REST", "bidirectional",
        "EfficastPort (inventory, work orders)",
        "Reserve parts, read/confirm work orders, check inventory — never machine control."),
]


def connectors_by_seam() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in CONNECTORS:
        out.setdefault(c.feeds, []).append(c.key)
    return out
