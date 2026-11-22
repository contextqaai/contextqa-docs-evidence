"""Use the same scoped citation endpoint from the CLI or a local MCP client."""

import argparse
import json
import os
from urllib.parse import urlsplit
import httpx


def search(question: str):
    origin = os.environ["DOCS_API_ORIGIN"].rstrip("/")
    u = urlsplit(origin)
    if (
        (
            u.scheme != "https"
            and not (
                u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost", "::1")
            )
        )
        or u.username
        or u.password
        or u.path
        or u.query
        or u.fragment
    ):
        raise ValueError("Use a bare HTTPS service origin or a local loopback origin.")
    response = httpx.post(
        origin + "/api/assistant/search",
        headers={"Authorization": "Bearer " + os.environ["DOCS_READER_KEY"]},
        json={"question": question},
        follow_redirects=False,
        timeout=12,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?")
    parser.add_argument("--mcp", action="store_true")
    args = parser.parse_args()
    if args.mcp:
        from mcp.server.fastmcp import FastMCP

        server = FastMCP("ContextQA documentation")
        server.tool(
            name="search_documentation",
            description="Find visible guide versions and review requests with citations.",
        )(search)
        server.run(transport="stdio")
    elif args.question:
        print(json.dumps(search(args.question), indent=2))
    else:
        parser.error("Supply a question or --mcp.")


if __name__ == "__main__":
    main()
