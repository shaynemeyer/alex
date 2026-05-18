"""
MCP server configurations for the Alex Researcher
"""
from agents.mcp import MCPServerStdio


def create_playwright_mcp_server(timeout_seconds=60):
    """Create a Playwright MCP server instance for web browsing.

    Uses the mcp-server-playwright binary installed globally in the Docker image
    to avoid npx fetching from the npm registry at Lambda runtime.

    Args:
        timeout_seconds: Client session timeout in seconds (default: 60)

    Returns:
        MCPServerStdio instance configured for Playwright
    """
    import glob
    import os

    args = [
        "--headless",
        "--isolated",
        "--no-sandbox",
        "--ignore-https-errors",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    ]

    if os.path.exists("/.dockerenv") or os.environ.get("AWS_EXECUTION_ENV"):
        chrome_paths = glob.glob("/root/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")
        if chrome_paths:
            args.extend(["--executable-path", chrome_paths[0]])

    # Use absolute path to locally installed binary — Lambda's PATH is minimal
    return MCPServerStdio(
        params={"command": "/app/node_modules/.bin/playwright-mcp", "args": args},
        client_session_timeout_seconds=timeout_seconds,
    )