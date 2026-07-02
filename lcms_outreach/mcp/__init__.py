"""
Helpers for using the geeViz MCP server with LCMS and tree canopy cover workflows.
"""

from .datasets import DATASETS, LCMS_DATASET, TCC_DATASET
from .prompts import RECIPES, format_recipes
from .server import main

__all__ = [
    "DATASETS",
    "LCMS_DATASET",
    "TCC_DATASET",
    "RECIPES",
    "format_recipes",
    "app",
    "main",
]


def __getattr__(name: str):
    if name == "app":
        from geeViz.mcp import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
