from dataclasses import dataclass

from .datasets import LCMS_DATASET, TCC_DATASET


@dataclass(frozen=True)
class PromptRecipe:
    key: str
    title: str
    prompt: str


RECIPES = (
    PromptRecipe(
        key="land-cover-change",
        title="LCMS land cover change",
        prompt=(
            f"Using the geeViz MCP, analyze {LCMS_DATASET.asset_id} over my area of interest. "
            "Use the Land_Cover band to create a change map, a stacked time-series chart, "
            "and an animated thumbnail or GIF. Summarize the largest class transitions."
        ),
    ),
    PromptRecipe(
        key="land-use-change",
        title="LCMS land use change",
        prompt=(
            f"Using the geeViz MCP, analyze {LCMS_DATASET.asset_id} over my area of interest. "
            "Use the Land_Use band to create a land use change chart and a Sankey-style "
            "transition summary for the start and end years."
        ),
    ),
    PromptRecipe(
        key="tree-canopy-change",
        title="Tree canopy cover change",
        prompt=(
            f"Using the geeViz MCP, load {TCC_DATASET.asset_id} and analyze the "
            f"{TCC_DATASET.bands[0]} band over my area of interest. Build start-year, "
            "end-year, and difference images, plus a mean tree canopy cover chart."
        ),
    ),
    PromptRecipe(
        key="integrated-report",
        title="Combined LCMS + TCC report",
        prompt=(
            f"Using the geeViz MCP, build an HTML or PDF report for my area of interest with "
            f"{LCMS_DATASET.asset_id} Land_Cover and Land_Use sections plus a "
            f"{TCC_DATASET.bands[0]} tree canopy cover change section from {TCC_DATASET.asset_id}. "
            "Include maps, charts, short narrative summaries, and output file paths."
        ),
    ),
)


def format_recipes() -> str:
    lines = ["Prompt recipes:"]
    for recipe in RECIPES:
        lines.append(f"- {recipe.key} — {recipe.title}")
        lines.append(f"  {recipe.prompt}")
    return "\n".join(lines)
