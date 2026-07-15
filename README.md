# LCMS Outreach — Workshop Notebooks

Python notebook examples accompanying the **Accessing and Using LCMS Data** public workshop. This repo focuses on the *code-based* portion of the workshop; hands-on GUI walkthroughs are covered in the live session.

---

## What is LCMS?

The [Landscape Change Monitoring System (LCMS)](https://www.fs.usda.gov/lcms) is an annual remote-sensing product produced by the USDA Forest Service Geospatial Technology and Applications Center (GTAC). It maps land cover, land use, and change processes across CONUS and SE Alaska at 30 m resolution from 1985 to present.

Three annual thematic products:

| Band | Description | Key Classes |
|------|-------------|-------------|
| `Land_Cover` | What is physically on the ground | Trees, Shrubs, Grass/Forb/Herb, Barren, Water, Snow/Ice |
| `Land_Use` | How the land is used or managed | Forest, Agriculture, Developed, Rangeland/Pasture, Other |
| `Change` | The dominant change process | Wildfire, Insect/Disease, Tree Removal, Successional Growth, Stable, … |

GEE catalog asset: **`USFS/GTAC/LCMS/v2024-10`**

---

## Repository Structure

```
lcms-outreach/
├── README.md                          ← you are here
├── requirements.txt                   ← Python dependencies
│
└── uinta_mountains_lcms_analysis.ipynb   ← Workshop example notebook
    Forest change, land use shifts, and disturbance (wildfire + insect/disease)
    in the Uinta Mountains, Utah/Wyoming, 1985–2024
```

> 📁 Additional notebooks and examples will be added here as the workshop series expands.

---

## Notebooks

### `uinta_mountains_lcms_analysis.ipynb`

**Research question:** How have forest cover and land use changed in the Uinta Mountains in relation to wildfire and insect/disease disturbance from the 1980s through today?

**What it covers:**

| Section | Analysis |
|---------|----------|
| 1 · Setup | GEE authentication and library imports |
| 2 · Study Area | Uinta Mountains bounding box + optional National Forest boundaries |
| 3 · Load LCMS | Filter collection to study area, inspect metadata |
| 4 · Interactive Map | geeViz map with Land Cover, Land Use, and Change layers |
| 5 · Land Cover Time Series | Stacked area chart of all LC classes 1985–2024 |
| 6 · Disturbance Time Series | Annual Wildfire, Insect/Disease, and Successional Growth trends |
| 7 · Land Use Sankey | Flow diagram of Land Use transitions across four decades |
| 8 · Combined Analysis | Dual-axis chart overlaying tree cover % with disturbance area % |
| 9 · Time-Lapse Map | Animated Change + Land Cover map with year slider |
| 10 · Bonus | Pixels that experienced both insect damage and fire |
| 11 · Takeaways | Interpretation guide and ideas for further exploration |

---

## Setup

### Prerequisites

- A **Google Earth Engine account** — [sign up free](https://earthengine.google.com/signup/)
- A **GEE Cloud Project** — [create one](https://developers.google.com/earth-engine/guides/access/cloud_projects) (free for non-commercial use)
- Python ≥ 3.9

### Install dependencies

```bash
pip install -r requirements.txt
```

### Authenticate with GEE

Run this once per machine:

```bash
earthengine authenticate
```

Or call `ee.Authenticate()` inside the first notebook cell (already included, commented out).

### Open a notebook

```bash
jupyter lab
# or
jupyter notebook
```

Then open `uinta_mountains_lcms_analysis.ipynb` and run cells top-to-bottom (`Kernel → Restart & Run All`).

> ⚠️ **Replace `'your-project-id'`** in the Setup cell with your actual GEE Cloud project ID before running.

---

## Key Libraries

| Library | Purpose |
|---------|---------|
| [`earthengine-api`](https://github.com/google/earthengine-api) | Python client for Google Earth Engine |
| [`geeViz`](https://github.com/redcastle-resources/geeViz) | USFS GTAC visualization and analysis toolkit built on EE |
| [`plotly`](https://plotly.com/python/) | Interactive charts (included via geeViz) |
| [`pandas`](https://pandas.pydata.org/) | DataFrame manipulation |

---

## Resources

- [LCMS Viewer (GUI)](https://apps.fs.usda.gov/lcms-viewer/) — explore LCMS data without code
- [LCMS GEE catalog page](https://developers.google.com/earth-engine/datasets/catalog/USFS_GTAC_LCMS_v2024-10)
- [geeViz documentation](https://github.com/redcastle-resources/geeViz)
- [USFS GTAC website](https://www.fs.usda.gov/about-agency/gtac)

---

## License

Code in this repository is released under the [MIT License](LICENSE).
LCMS data are a USDA Forest Service product; see their [data use policy](https://www.fs.usda.gov/lcms) for citation requirements.
