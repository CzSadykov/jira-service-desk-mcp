"""MCP server for Jira Service Management (Service Desk)."""

from __future__ import annotations

import logging
import sys

import click
from dotenv import load_dotenv

from .server import mcp


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="MCP transport protocol.",
)
@click.option("--host", default="0.0.0.0", help="Host for SSE transport.")
@click.option("--port", default=8000, type=int, help="Port for SSE transport.")
@click.option("--log-level", default="INFO", help="Logging level.")
def main(transport: str, host: str, port: int, log_level: str) -> None:
    """Start the Jira Service Desk MCP server."""
    load_dotenv()

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
