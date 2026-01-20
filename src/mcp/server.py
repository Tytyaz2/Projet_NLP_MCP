# src/mcp/server.py
"""
Serveur MCP utilisant FastMCP pour exposer les outils à Claude Desktop.
"""

from mcp.server.fastmcp import FastMCP

# Créer le serveur MCP
mcp = FastMCP("file-classifier")

# Exporter pour utilisation dans les autres modules
__all__ = ["mcp"]
