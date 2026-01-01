@echo off
:: Navigate to the directory where the script is located
cd /d "%~dp0"

:: Launch the MCP server in a separate window
start "FastMCP Server" uv run fastmcp run main.py --transport sse --port 8000

echo MCP Server is launching in a new window...
pause