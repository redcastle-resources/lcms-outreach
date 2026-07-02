from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetDefinition:
    name: str
    asset_id: str
    bands: tuple[str, ...]
    summary: str


LCMS_DATASET = DatasetDefinition(
    name="LCMS",
    asset_id="USFS/GTAC/LCMS/v2024-10",
    bands=("Land_Cover", "Land_Use", "Change"),
    summary="USFS LCMS image collection for land cover, land use, and change products.",
)

TCC_DATASET = DatasetDefinition(
    name="TCC",
    asset_id="USGS/NLCD_RELEASES/2016_REL",
    bands=("percent_tree_cover",),
    summary="NLCD tree canopy cover imagery via the percent_tree_cover band.",
)

DATASETS = (LCMS_DATASET, TCC_DATASET)


def format_datasets() -> str:
    lines = ["Datasets:"]
    for dataset in DATASETS:
        bands = ", ".join(dataset.bands)
        lines.append(f"- {dataset.name}: {dataset.asset_id}")
        lines.append(f"  bands: {bands}")
        lines.append(f"  {dataset.summary}")
    return "\n".join(lines)
