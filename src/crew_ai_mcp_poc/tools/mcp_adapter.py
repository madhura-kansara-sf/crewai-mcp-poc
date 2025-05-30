from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
import os

def get_mcp_tools():
    # Define MCP connection to context_server.py
    server_params = StdioServerParameters(
        command="python3",
        args=["src/crew_ai_mcp_poc/servers/context_server.py"],
        env={"UV_PYTHON": "3.12", **os.environ}
    )

    return MCPServerAdapter(server_params)

