"""Entry point for ncbi-datasets-mcp: stdio or HTTP transport."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env so NCBI_API_KEY (and MCP_* vars) are set when run from any cwd
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .server import mcp

# Transport: stdio (default) or http
# For HTTP: set MCP_TRANSPORT=http; default host 127.0.0.1 (localhost only)
def main() -> None:
    transport = (os.environ.get("MCP_TRANSPORT") or "stdio").strip().lower()
    if transport == "http":
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        port = int(os.environ.get("MCP_PORT", "8000"))
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
