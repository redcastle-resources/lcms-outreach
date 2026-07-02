from __future__ import annotations

import sys

from .datasets import format_datasets
from .prompts import format_recipes


def _help_text() -> str:
    return "\n".join(
        [
            "lcms-outreach MCP wrapper for geeViz.",
            "",
            "Usage:",
            "  python -m lcms_outreach.mcp           Run the geeViz MCP server.",
            "  python -m lcms_outreach.mcp --recipes Show LCMS/TCC prompt recipes.",
            "  python -m lcms_outreach.mcp --help    Show this help.",
            "",
            "Pass-through server flags:",
            "  --sandbox      Run geeViz MCP in sandbox mode.",
            "  --no-sandbox   Disable geeViz MCP sandbox mode.",
            "",
            format_datasets(),
            "",
            "Use --recipes to print prompt text you can paste into an MCP-enabled client.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if any(arg in {"-h", "--help"} for arg in args):
        print(_help_text())
        return 0

    if "--recipes" in args:
        print(format_recipes())
        return 0

    from geeViz.mcp.server import main as geeviz_main

    original_argv = sys.argv[:]
    try:
        sys.argv = [original_argv[0], *args]
        geeviz_main()
    finally:
        sys.argv = original_argv
    return 0
