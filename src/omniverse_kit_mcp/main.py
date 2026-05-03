"""Entry point for the Isaac Sim Validation MCP Server."""

from __future__ import annotations

import logging

from omniverse_kit_mcp.config import load_config
from omniverse_kit_mcp.mcp.server import create_mcp_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    config = load_config()
    mcp = create_mcp_server(config)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
