from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "agent"
FORBIDDEN = ("mcp", "governance", "GATEWAY_MCP_URL")


def test_concierge_does_not_depend_on_the_governance_project() -> None:
    for path in ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in FORBIDDEN:
            assert name not in text, f"{path.name} mentions {name}"
        tree = ast.parse(text)
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                assert not module.startswith("gateway"), path.name
                assert module != "mcp", path.name
