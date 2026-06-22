"""Industrial integration layer: ISA-95 hierarchy, Unified-Namespace topics, and the connector catalog.

See docs/INDUSTRY_LANDSCAPE.md (how real platforms deliver agents) and docs/INTEGRATION_ARCHITECTURE.md.
"""

from app.integration.connectors import CONNECTORS, ConnectorSpec, connectors_by_seam
from app.integration.isa95 import ISA95_LEVELS, AssetPath, asset_path, sparkplug_topic, uns_topic

__all__ = [
    "ISA95_LEVELS", "AssetPath", "asset_path", "uns_topic", "sparkplug_topic",
    "CONNECTORS", "ConnectorSpec", "connectors_by_seam",
]
