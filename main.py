import logging
from websearx_tool.server import mcp

if __name__ == "__main__":
    logging.info("Starting WebSearx MCP Server...")
    mcp.run()