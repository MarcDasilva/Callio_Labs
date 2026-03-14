"""Entry point for ncbi-datasets-mcp: stdio or HTTP transport."""

from __future__ import annotations

import os

from .server import mcp

# Transport: stdio (default) or http
# For HTTP: set MCP_TRANSPORT=http, optional MCP_HOST=0.0.0.0, MCP_PORT=8000
def main() -> None:
    transport = (os.environ.get("MCP_TRANSPORT") or "stdio").strip().lower()
    if transport == "http":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8000"))
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
