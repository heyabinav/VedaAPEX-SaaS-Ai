"""Connector registry - auto-discovers and registers all connectors."""

import logging
from typing import Dict, Optional

from app.connectors.base import BaseConnector

logger = logging.getLogger("connectors.registry")


class ConnectorRegistry:
    _connectors: Dict[str, BaseConnector] = {}

    @classmethod
    def register(cls, connector: BaseConnector) -> None:
        cls._connectors[connector.provider] = connector
        logger.info("Registered connector: %s", connector.provider)

    @classmethod
    def get(cls, provider: str) -> Optional[BaseConnector]:
        return cls._connectors.get(provider.lower())

    @classmethod
    def all(cls) -> Dict[str, BaseConnector]:
        return dict(cls._connectors)

    @classmethod
    def providers(cls) -> list:
        return list(cls._connectors.keys())


connector_registry = ConnectorRegistry()


def _register_all():
    from app.connectors.google.connector import GoogleConnector
    from app.connectors.github.connector import GitHubConnector
    from app.connectors.notion.connector import NotionConnector
    from app.connectors.figma.connector import FigmaConnector
    from app.connectors.canva.connector import CanvaConnector

    connector_registry.register(GoogleConnector())
    connector_registry.register(GitHubConnector())
    connector_registry.register(NotionConnector())
    connector_registry.register(FigmaConnector())
    connector_registry.register(CanvaConnector())

    logger.info("All connectors registered: %s", connector_registry.providers())


_register_all()
