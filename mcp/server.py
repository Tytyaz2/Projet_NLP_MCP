# mcp/server.py


import time
from typing import Callable, Any, Dict

# ─────────────────────────────────────────
# Décorateur pour enregistrer un "tool"
# ─────────────────────────────────────────
_tools: Dict[str, Callable] = {}

def tool(name: str = None):
    """
    Décorateur pour déclarer une fonction comme outil MCP.
    """
    def decorator(func: Callable):
        key = name or func.__name__
        _tools[key] = func
        return func
    return decorator

# ─────────────────────────────────────────
# Serveur MCP minimal
# ─────────────────────────────────────────
class Server:
    def __init__(self, name: str = "mcp-server"):
        self.name = name
        self.tools = _tools

    def run(self):
        """
        Démarrage minimal du serveur MCP.
        Pour l'instant, il liste juste les outils disponibles
        et permet de les appeler depuis le code.
        """
        print(f"=== MCP Server '{self.name}' démarré ===")
        print("Outils disponibles :")
        for t in self.tools:
            print(f" - {t}")
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("Serveur arrêté manuellement.")