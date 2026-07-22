"""
McDonald-Dunn Research Forest: Forest Recovery from Active Timber Management 1985-2025
Using USFS Landscape Change Monitoring System (LCMS) in Google Earth Engine

Vet script — mirrors the macdunn_harvest_recovery.ipynb notebook end-to-end.
Run from the repo root with the venv active:
    python examples/macdunn_harvest_recovery.py
"""

# ==============================================================================
# 1 · Setup — Imports and Authentication
# ==============================================================================
import os
import pathlib
import json
import webbrowser

import ee
from IPython.display import display, HTML

# ── Authentication ─────────────────────────────────────────────────────────────
# Run once per machine/account, then comment out:
# ee.Authenticate()

# ── ee.Initialize MUST come before geeViz imports ─────────────────────────────
EE_PROJECT = 'rcr-gee'  # replace with your GEE Cloud project ID
ee.Initialize(project=EE_PROJECT)

# ── Force in-process HTTP server (avoids stale-layer bug) ─────────────────────
os.environ['GEEVIZ_EEAUTH_MODE'] = 'auto'

import geeViz.getImagesLib as gil
import geeViz.geeView
import geeViz.getSummaryAreasLib as sal
from geeViz.outputLib import charts as cl

Map = gil.Map
Map.port = 8080
Map.project = EE_PROJECT
Map.clearMap()

test = ee.Image(1).getInfo()
print(test, '\nEarth Engine initialized successfully.')


# ==============================================================================
# 2 · Study Area
# ==============================================================================
START_YEAR = 1984
END_YEAR   = 2024

# ── Export format flags ───────────────────────────────────────────────────────
EXPORT_HTML = False  # save interactive Plotly/geeViz charts as .html
EXPORT_CSV  = False   # save underlying DataFrames as .csv
EXPORT_DIR  = pathlib.Path('./exports')
# Set EXPORT_DIR = None to save alongside this script instead

study_area = ee.Geometry.BBox(-123.46, 44.60, -123.22, 44.82)

print("Study date range:", START_YEAR, "to", END_YEAR)
print('Study area type:', study_area.getInfo()['type'])
area_km2 = study_area.area(maxError=500).divide(1e6).getInfo()
print(f'Bounding box area : {area_km2:,.0f} km2  (~46.5 km2 combined forest; bbox includes surrounding context)')

# ── McDonald-Dunn stand boundaries from local GeoJSON ─────────────────────────
_data_dir = pathlib.Path(__file__).resolve().parent.parent / 'data'
with open(_data_dir / 'macdunn_boundary.geojson') as f:
    _boundary_gj = json.load(f)
macdunn_boundary_fc = ee.FeatureCollection(_boundary_gj['features'])

with open(_data_dir / 'macdunn_age_class.geojson') as f:
    _stands_gj = json.load(f)
macdunn_stands_fc = ee.FeatureCollection(_stands_gj['features'])

# ==============================================================================
# 3 · Load LCMS Data
# ==============================================================================
LCMS_ASSET_FOR_PROPERTIES = 'USFS/GTAC/LCMS/v2024-10'
LCMS_ASSET = 'projects/gtac-data-publish/assets/LCMS/Product_Version/2025-11'

lcms = ee.ImageCollection(LCMS_ASSET_FOR_PROPERTIES).filterBounds(study_area)

n_images = lcms.size().getInfo()
years    = lcms.aggregate_array('year').distinct().sort().getInfo()
bands    = lcms.first().bandNames().getInfo()

print(f'Images in collection : {n_images}')
print(f'Years                : {years[0]}-{years[-1]}')
print(f'Bands                : {bands}')

sample_img      = ee.ImageCollection(LCMS_ASSET_FOR_PROPERTIES).first()
change_names    = sample_img.get('Change_class_names').getInfo()
change_values   = sample_img.get('Change_class_values').getInfo()
change_palettes = sample_img.get('Change_class_palette').getInfo()

change_img = lcms.first().select('Change')
print('Change image properties:')
for key in change_img.propertyNames().getInfo():
    print(f'  {key}: {change_img.get(key).getInfo()}')


# ==============================================================================
# 4 · Interactive Map — Current Forest State and Harvest History
# ==============================================================================
Map.clearMap()

lcms_most_recent = lcms.filter(ee.Filter.eq('year', END_YEAR))

Map.addLayer(
    lcms_most_recent.select('Land_Cover'),
    {'autoViz': True, 'canAreaChart': True},
    f'Land Cover {END_YEAR}',
    True,
)

lcms_most_recent_change = lcms_most_recent.select('Change').first().clip(study_area)
Map.addLayer(
    lcms_most_recent_change,
    {'autoViz': True, 'canAreaChart': True},
    f'Most Recent Change Agent ({END_YEAR})',
    True,
)

# .mode() drops all image metadata; copyProperties() restores the class
# properties (palette, names, values) that autoViz needs to symbolize.
lcms_most_common_change = (
    ee.Image(lcms.select('Change').mode())
    .clip(study_area)
    .copyProperties(sample_img)
)
Map.addLayer(
    lcms_most_common_change,
    {'autoViz': True, 'canAreaChart': True},
    'Most Common Change Agent (1985-2025)',
    False,
)

lcms_most_severe_change = (
    ee.Image(lcms.select('Change').reduce(ee.Reducer.min()))
    .rename('Change')   # reducer appends '_min'; rename back so autoViz finds Change_class_* props
    .clip(study_area)
    .copyProperties(sample_img)
)
Map.addLayer(
    lcms_most_severe_change,
    {'autoViz': True, 'canAreaChart': True},
    'Most Severe Change Agent (1985-2025)',
    False,
)

name_to_val = dict(zip(change_names, change_values))
TREE_REMOVAL_VAL = name_to_val.get(
    'Tree Removal',
    name_to_val.get('Non-Fire Mechanical', 5),
)
print(f'Tree Removal class value in this LCMS version: {TREE_REMOVAL_VAL}')

ever_harvested = (
    lcms.select('Change')
    .map(lambda img: img.eq(TREE_REMOVAL_VAL))
    .max()
    .selfMask()
    .rename('ever_harvested')
)
ever_harvested = ever_harvested.set({
    'ever_harvested_class_values':  [1],
    'ever_harvested_class_names':   ['Tree Removal detected (any year 1985-2025)'],
    'ever_harvested_class_palette': ['c47b1e'],
})
Map.addLayer(ever_harvested, {'autoViz': True}, 'Ever Harvested 1985-2025', True)

Map.addLayer(
    macdunn_boundary_fc,
    {'layerType': 'geeVectorImage', 'strokeColor': 'cccccc', 'strokeWidth': 1,
     'fillColor': '00000000'},
    'McDonald-Dunn Boundary',
    True,
)

# ── Stand age raster — vector painted to image, young=light blue, old=dark blue
age_raster = (
    macdunn_stands_fc
    .reduceToImage(properties=['Age'], reducer=ee.Reducer.first())
    .rename('Age')
)
Map.addLayer(
    age_raster,
    {'min': 9, 'max': 340,
     'palette': ['dce9f5', '9ecae1', '4292c6', '2171b5', '08519c', '08306b']},
    'Stand Age (years)',
    True,
)
# Thin boundary outlines on top of the raster for stand delineation
Map.addLayer(
    macdunn_stands_fc,
    {'layerType': 'geeVectorImage', 'strokeColor': '00000066', 'strokeWidth': 0.5,
     'fillColor': '00000000'},
    'McDonald-Dunn Stands',
    True,
)

Map.addLayer(
    ee.Feature(study_area, {}),
    {'layerType': 'geeVector', 'strokeColor': 'ffff00', 'strokeWidth': 2.5,
     'fillColor': '00000000'},
    'McDonald-Dunn BBox',
    False,
)

Map.setCenter(-123.34, 44.70, 11)
Map.view()
input('Section 4 map open — press Enter to continue...')

# Most recent Tree Removal year per pixel.
# Build a constant-year image and mask it to harvest pixels — avoids the uint8
# overflow that occurs when multiplying a binary (0/1) mask by a 4-digit year.
# .max() across years: unmasked pixels compete on year value; pixels masked in
# every year stay masked in the output (never harvested → no value shown).
harvest_year = (
    lcms.select('Change')
    .map(lambda img: ee.Image.constant(ee.Number(img.get('year')))
                       .toFloat()                      # cast to generic Float — without this,
                       .updateMask(img.eq(TREE_REMOVAL_VAL))  # each year gets type Float<YYYY,YYYY>
                       .rename('harvest_year'))         # and .max() rejects the heterogeneous collection
    .max()
)

# Continuous year values — autoViz looks for class properties (finds none) and
# renders black. Use explicit min/max/palette instead.
Map.addLayer(
    harvest_year,
    {'min': START_YEAR, 'max': END_YEAR,
     'palette': ['ffffb2', 'fecc5c', 'fd8d3c', 'f03b20', 'bd0026']},
    'Most Recent Harvest Year',
    True,
)


# ==============================================================================
# 5 · Harvest Comparison Polygons
# ==============================================================================
# ── Representative stand per age class (largest non-agricultural stand by area) ─
# FID : display name used as chart/layer label throughout
_STAND_FIDS = {
    450: '9-20 yrs (Stand 020408)',
    401: '20-40 yrs (Stand 010207)',
    62:  '40-80 yrs (Stand 020503)',
    165: '80-120 yrs (Stand 041810)',
    312: '120-200 yrs (Stand 070414)',
    251: '200-500 yrs (Stand 080603)',
}

harvest_areas = {}
for feat in _stands_gj['features']:
    fid = int(feat['properties']['FID'])
    if fid not in _STAND_FIDS or not feat.get('geometry'):
        continue
    label  = _STAND_FIDS[fid]
    coords = feat['geometry']['coordinates']
    gtype  = feat['geometry']['type']
    if gtype == 'Polygon':
        harvest_areas[label] = ee.Geometry.Polygon(coords)
    else:
        harvest_areas[label] = ee.Geometry.MultiPolygon(coords)

# Re-order by age class (youngest → oldest) regardless of GeoJSON feature order
_AGE_CLASS_ORDER = list(_STAND_FIDS.values())
harvest_areas = {k: harvest_areas[k] for k in _AGE_CLASS_ORDER if k in harvest_areas}

print('Representative stand areas (youngest → oldest):')
for name, geom in harvest_areas.items():
    area = geom.area(maxError=100).divide(1e6).getInfo()
    print(f'  {name:40s}: {area:.2f} km2')

# Light-to-dark blue mirrors the age raster palette (young = pale, old = dark)
POLY_COLORS = {
    '9-20 yrs (Stand 020408)':   'b3d9f7',
    '20-40 yrs (Stand 010207)':  '6baed6',
    '40-80 yrs (Stand 020503)':  '4292c6',
    '80-120 yrs (Stand 041810)': '2171b5',
    '120-200 yrs (Stand 070414)':'08519c',
    '200-500 yrs (Stand 080603)':'08306b',
}

for name, geom in harvest_areas.items():
    c = POLY_COLORS[name]
    Map.addLayer(
        ee.Feature(geom, {}),
        {'layerType': 'geeVector', 'strokeColor': c, 'strokeWidth': 3,
         'fillColor': c + '35'},
        name,
    )

Map.addLayer(
    macdunn_boundary_fc,
    {'layerType': 'geeVectorImage', 'strokeColor': 'cccccc', 'strokeWidth': 1,
     'fillColor': '00000000'},
    'McDonald-Dunn Stands',
    True,
)
Map.setCenter(-123.34, 44.70, 11)
Map.view()
input('Section 5 map open — press Enter to continue...')


# ==============================================================================
# 6 · Recovery Trajectories — Land Cover Through Time
# ==============================================================================
import os as _os
_script_dir = _os.path.dirname(_os.path.abspath(__file__))
# Resolve output directory — use EXPORT_DIR if set, otherwise script folder
if EXPORT_DIR:
    _script_dir = str(EXPORT_DIR)
    pathlib.Path(_script_dir).mkdir(parents=True, exist_ok=True)
print(f'Output directory: {_script_dir}')

lc_results = {}

for name, geom in harvest_areas.items():
    lcms_poly = ee.ImageCollection(LCMS_ASSET).filterBounds(geom)
    slug = (
        name[:18]
        .replace(' ', '_').replace('(', '').replace(')', '')
        .replace('~', '').replace('-', '_').strip('_')
    )
    result = cl.summarize_and_chart(
        lcms_poly,
        geometry=geom,
        band_names='Land_Cover',
        scale=30,
        area_format='Percentage',
        title=f'Land Cover — {name}',
        chart_type='line',
        stacked=True,
        date_format='YYYY',
        width=950,
        height=440,
    )
    lc_results[name] = result

    if EXPORT_HTML:
        fname = _os.path.join(_script_dir, f'macdunn_lc_{slug}.html')
        cl.save_chart_html(result['chart'], fname)
        print(f'Saved: {fname}')
    if EXPORT_CSV:
        csv_fname = _os.path.join(_script_dir, f'macdunn_lc_{slug}.csv')
        result['df'].to_csv(csv_fname)
        print(f'Saved: {csv_fname}')

print('Section 6 complete — land cover charts saved.')


# ==============================================================================
# 6a · Inspect the Recovery Data — Trees column comparison table
# ==============================================================================
import pandas as pd

trees_pct = {}
for name, result in lc_results.items():
    df = result['df']
    trees_col = next(
        (c for c in df.columns if 'Trees' in c and 'Tall' not in c),
        None,
    )
    if trees_col:
        trees_pct[name] = df[trees_col].round(1)
    else:
        print(f'Warning: Trees column not found for "{name}". Columns: {df.columns.tolist()}')

if trees_pct:
    trees_df = pd.DataFrame(trees_pct)
    trees_df.index.name = 'Year'
    print('\nAnnual Trees cover (%) by harvest area:\n')
    print(trees_df.to_markdown())


# ==============================================================================
# 7 · Change Agent Signatures — Tree Removal and Successional Growth
# ==============================================================================
change_results = {}

for name, geom in harvest_areas.items():
    lcms_poly = ee.ImageCollection(LCMS_ASSET_FOR_PROPERTIES).filterBounds(geom)
    slug = (
        name[:18]
        .replace(' ', '_').replace('(', '').replace(')', '')
        .replace('~', '').replace('-', '_').strip('_')
    )
    result = cl.summarize_and_chart(
        lcms_poly,
        geometry=geom,
        band_names='Change',
        scale=30,
        area_format='Percentage',
        title=f'Change Agents — {name}',
        chart_type='line',
        stacked=False,
        date_format='YYYY',
        width=950,
        height=440,
    )
    change_results[name] = result

    if EXPORT_HTML:
        fname = _os.path.join(_script_dir, f'macdunn_change_{slug}.html')
        cl.save_chart_html(result['chart'], fname)
        print(f'Saved: {fname}')
    if EXPORT_CSV:
        csv_fname = _os.path.join(_script_dir, f'macdunn_change_{slug}.csv')
        result['df'].to_csv(csv_fname)
        print(f'Saved: {csv_fname}')

print('Section 7 complete — change agent charts saved.')


# ==============================================================================
# 8 · Combined Comparison — Tree Cover Recovery Across All Management Zones
# ==============================================================================
import plotly.graph_objects as go

LINE_COLORS = {
    '9-20 yrs (Stand 020408)':   '#b3d9f7',
    '20-40 yrs (Stand 010207)':  '#6baed6',
    '40-80 yrs (Stand 020503)':  '#4292c6',
    '80-120 yrs (Stand 041810)': '#2171b5',
    '120-200 yrs (Stand 070414)':'#08519c',
    '200-500 yrs (Stand 080603)':'#08306b',
}
DASH_STYLES = ['solid', 'dash', 'dot', 'dashdot', 'longdash', 'longdashdot']

fig = go.Figure()

for (name, result), dash in zip(lc_results.items(), DASH_STYLES):
    df = result['df']
    trees_col = next(
        (c for c in df.columns if 'Trees' in c and 'Tall' not in c),
        None,
    )
    if trees_col:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[trees_col].values,
            name=name,
            mode='lines+markers',
            line=dict(color=LINE_COLORS[name], width=2.5, dash=dash),
            marker=dict(size=4),
        ))

fig.update_layout(
    title='McDonald-Dunn Research Forest — Tree Cover Recovery by Management Zone 1985-2025',
    xaxis=dict(title='Year', tickmode='linear', dtick=5),
    yaxis=dict(title='Trees (% of polygon area)', range=[0, 100]),
    legend=dict(orientation='h', yanchor='top', y=-0.20, xanchor='left', x=0),
    width=1050,
    height=550,
    template='plotly_white',
)

comparison_path = _os.path.join(_script_dir, 'macdunn_recovery_comparison.html')
if EXPORT_HTML:
    fig.write_html(comparison_path)
    print(f'Comparison chart saved to {comparison_path}')
if EXPORT_CSV and trees_pct:
    trees_csv = _os.path.join(_script_dir, 'macdunn_recovery_comparison.csv')
    pd.DataFrame(trees_pct).to_csv(trees_csv)
    print(f'Trees comparison CSV saved to {trees_csv}')


# ==============================================================================
# 8b · Tree Canopy Cover (TCC) Trajectories and Combined Comparison
# ==============================================================================
TCC_ASSET = 'projects/gtac-data-publish/assets/TCC/Product_Version/2025-6'
TCC_BAND  = 'Science_Percent_Tree_Canopy_Cover'

tcc = (
    ee.ImageCollection(TCC_ASSET)
    .filter(ee.Filter.inList('study_area', ['CONUS']))
    .filterBounds(study_area)
)

tcc_results = {}

for name, geom in harvest_areas.items():
    slug = (
        name[:18]
        .replace(' ', '_').replace('(', '').replace(')', '')
        .replace('~', '').replace('-', '_').strip('_')
    )
    result = cl.summarize_and_chart(
        tcc.filterBounds(geom),
        geometry=geom,
        band_names=TCC_BAND,
        scale=30,
        area_format='Mean',          # continuous 0-100 % value — mean per polygon
        title=f'Tree Canopy Cover (TCC) — {name}',
        chart_type='line',
        date_format='YYYY',
        width=950,
        height=440,
    )
    tcc_results[name] = result
    if EXPORT_HTML:
        fname = _os.path.join(_script_dir, f'macdunn_tcc_{slug}.html')
        cl.save_chart_html(result['chart'], fname)
        print(f'Saved: {fname}')
    if EXPORT_CSV:
        csv_fname = _os.path.join(_script_dir, f'macdunn_tcc_{slug}.csv')
        result['df'].to_csv(csv_fname)
        print(f'Saved: {csv_fname}')

print('Section 8b complete — per-polygon TCC charts saved.')

# ── Combined TCC comparison across all management zones ───────────────────────
fig_tcc = go.Figure()

for (name, result), dash in zip(tcc_results.items(), DASH_STYLES):
    df = result['df']
    # column name is typically the band name or contains 'Canopy'
    tcc_col = next(
        (c for c in df.columns if 'Canopy' in c or 'canopy' in c),
        df.columns[0] if len(df.columns) else None,
    )
    if tcc_col:
        fig_tcc.add_trace(go.Scatter(
            x=df.index,
            y=df[tcc_col].values,
            name=name,
            mode='lines+markers',
            line=dict(color=LINE_COLORS[name], width=2.5, dash=dash),
            marker=dict(size=4),
        ))

fig_tcc.update_layout(
    title='McDonald-Dunn Research Forest — Science TCC by Management Zone 1985-2025',
    xaxis=dict(title='Year', tickmode='linear', dtick=5),
    yaxis=dict(title='Mean Tree Canopy Cover (%)', range=[0, 100]),
    legend=dict(orientation='h', yanchor='top', y=-0.20, xanchor='left', x=0),
    width=1050,
    height=550,
    template='plotly_white',
)

tcc_comparison_path = _os.path.join(_script_dir, 'macdunn_tcc_comparison.html')
if EXPORT_HTML:
    fig_tcc.write_html(tcc_comparison_path)
    print(f'TCC comparison chart saved to {tcc_comparison_path}')
if EXPORT_CSV:
    tcc_rows = {}
    for name, result in tcc_results.items():
        tcc_col = next((c for c in result['df'].columns if 'Canopy' in c or 'canopy' in c),
                       result['df'].columns[0] if len(result['df'].columns) else None)
        if tcc_col:
            tcc_rows[name] = result['df'][tcc_col]
    if tcc_rows:
        tcc_csv = _os.path.join(_script_dir, 'macdunn_tcc_comparison.csv')
        import pandas as _pd
        _pd.DataFrame(tcc_rows).to_csv(tcc_csv)
        print(f'TCC comparison CSV saved to {tcc_csv}')


# ==============================================================================
# 8c · TCC + Change Agent — Side-by-Side per AOI
# ==============================================================================
# Two-panel subplot per harvest area: TCC % on top, key change agents below.
# Shared x-axis lets you read harvest events and TCC response in one view.
from plotly.subplots import make_subplots

for name, geom in harvest_areas.items():
    if name not in change_results or name not in tcc_results:
        print(f'Skipping {name} — missing change or TCC data')
        continue

    change_df = change_results[name]['df']
    tcc_df    = tcc_results[name]['df']

    # ── locate columns ─────────────────────────────────────────────────────────
    tcc_col = next(
        (c for c in tcc_df.columns if 'Canopy' in c or 'canopy' in c),
        tcc_df.columns[0] if len(tcc_df.columns) else None,
    )
    removal_col = next(
        (c for c in change_df.columns if 'Removal' in c or 'removal' in c), None
    )
    growth_col = next(
        (c for c in change_df.columns if 'Successional' in c or 'Growth' in c), None
    )

    fig_combo = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        subplot_titles=('Science Tree Canopy Cover (%)', 'LCMS Change Agents (% of area)'),
        vertical_spacing=0.14,
        row_heights=[0.45, 0.55],
    )

    # ── top panel: TCC ────────────────────────────────────────────────────────
    if tcc_col:
        fig_combo.add_trace(go.Scatter(
            x=tcc_df.index, y=tcc_df[tcc_col].values,
            name='Science TCC %', mode='lines+markers',
            line=dict(color='#27ae60', width=2.5),
            marker=dict(size=4),
        ), row=1, col=1)

    # ── bottom panel: Tree Removal + Successional Growth ──────────────────────
    for col, label, color in [
        (removal_col, 'Tree Removal',          '#e84c1e'),
        (growth_col,  'Successional Growth',   '#4caf50'),
    ]:
        if col:
            fig_combo.add_trace(go.Scatter(
                x=change_df.index, y=change_df[col].values,
                name=label, mode='lines+markers',
                line=dict(color=color, width=2),
                marker=dict(size=3),
            ), row=2, col=1)

    slug = (
        name[:18]
        .replace(' ', '_').replace('(', '').replace(')', '')
        .replace('~', '').replace('-', '_').strip('_')
    )
    fig_combo.update_layout(
        title=f'TCC and Change Agents — {name}',
        yaxis=dict(title='TCC (%)', range=[0, 100]),
        yaxis2=dict(title='% of area', range=[0, 100]),
        xaxis2=dict(title='Year', tickmode='linear', dtick=5),
        height=680, width=1000,
        template='plotly_white',
        legend=dict(orientation='h', yanchor='top', y=-0.10, xanchor='left', x=0),
    )

    fname = _os.path.join(_script_dir, f'macdunn_tcc_change_{slug}.html')
    fig_combo.write_html(fname)
    print(f'Saved: {fname}')

print('Section 8c complete — TCC + change combo charts saved.')


# ==============================================================================
# 9 · Land Use Transitions — Sankey Diagram
# ==============================================================================
lu_sankey = cl.summarize_and_chart(
    lcms,
    geometry=study_area,
    band_names='Land_Use',
    scale=120,
    area_format='Percentage',
    title=f'McDonald-Dunn Research Forest — Land Use Transitions 1985 -> 1995 -> 2010 -> {END_YEAR}',
    sankey=True,
    transition_periods=[1985, 1995, 2010, END_YEAR],
    min_percentage=0.5,
    width=1000,
    height=600,
)

sankey_path = _os.path.join(_script_dir, 'macdunn_land_use_sankey.html')
if EXPORT_HTML:
    cl.save_chart_html(lu_sankey['chart'], sankey_path)
    print(f'Sankey saved to {sankey_path}')
if EXPORT_CSV and 'df' in lu_sankey:
    sankey_csv = _os.path.join(_script_dir, 'macdunn_land_use_sankey.csv')
    lu_sankey['df'].to_csv(sankey_csv)
    print(f'Sankey CSV saved to {sankey_csv}')


# ==============================================================================
# 9a · Land Use Transition Matrices
# ==============================================================================
if 'matrix' in lu_sankey:
    for period_key, mat in lu_sankey['matrix'].items():
        print(f'### {period_key}')
        print(mat.to_markdown())
        print()


# ==============================================================================
# 10 · Time-Lapse Map
# ==============================================================================
Map.clearMap()

Map.addTimeLapse(
    lcms.select('Change'),
    {'autoViz': True, 'canAreaChart': True},
    'Change Agent (Annual)',
    visible=True,
)

Map.addTimeLapse(
    lcms.select('Land_Cover'),
    {'autoViz': True, 'canAreaChart': True},
    'Land Cover (Annual)',
    visible=False,
)

for name, geom in harvest_areas.items():
    c = POLY_COLORS[name]
    Map.addLayer(
        ee.Feature(geom, {}),
        {'layerType': 'geeVector', 'strokeColor': c, 'strokeWidth': 3,
         'fillColor': '00000000'},
        name,
        False,
    )

Map.addLayer(
    macdunn_boundary_fc,
    {'layerType': 'geeVectorImage', 'strokeColor': 'cccccc', 'strokeWidth': 1,
     'fillColor': '00000000'},
    'McDonald-Dunn Stands',
    True,
)
Map.addLayer(
    ee.Feature(study_area, {}),
    {'layerType': 'geeVector', 'strokeColor': 'ffffff', 'strokeWidth': 2,
     'fillColor': '00000000'},
    'McDonald-Dunn Study Area',
)

Map.setCenter(-123.34, 44.70, 11)
Map.view()
input('Section 10 time-lapse map open — press Enter to continue...')


# ==============================================================================
# 11 · Classify Recovery Stages Across the Study Area
# ==============================================================================
Map.clearMap()

years_as_trees = (
    lcms.select('Land_Cover')
    .map(lambda img: img.eq(1).rename('is_trees'))
    .sum()
    .rename('years_as_trees')
)

recovery_stage = (
    ee.Image(1)
    .where(years_as_trees.gt(5),  2)
    .where(years_as_trees.gt(15), 3)
    .where(years_as_trees.gt(29), 4)
    .rename('recovery_stage')
    .updateMask(years_as_trees.gte(0))
)

recovery_stage = recovery_stage.set({
    'recovery_stage_class_values':  [1, 2, 3, 4],
    'recovery_stage_class_names':   [
        'Early seral (0-5 yrs Trees)',
        'Mid seral (6-15 yrs Trees)',
        'Late seral (16-29 yrs Trees)',
        'Mature/established stand (30-41 yrs Trees)',
    ],
    'recovery_stage_class_palette': ['f7dc6f', 'e67e22', '27ae60', '1a5276'],
})

Map.addLayer(
    lcms_most_recent.select('Land_Cover'),
    {'autoViz': True, 'canAreaChart': True},
    f'Land Cover {END_YEAR}',
    False,
)
Map.addLayer(
    recovery_stage,
    {'autoViz': True, 'canAreaChart': True},
    'Recovery Stage (years as Trees, 1985-2025)',
    True,
)

for name, geom in harvest_areas.items():
    c = POLY_COLORS[name]
    Map.addLayer(
        ee.Feature(geom, {}),
        {'layerType': 'geeVector', 'strokeColor': c, 'strokeWidth': 3,
         'fillColor': '00000000'},
        name,
        True,
    )

Map.addLayer(
    macdunn_boundary_fc,
    {'layerType': 'geeVectorImage', 'strokeColor': 'cccccc', 'strokeWidth': 1,
     'fillColor': '00000000'},
    'McDonald-Dunn Boundary',
    True,
)
Map.addLayer(
    ee.Feature(study_area, {}),
    {'layerType': 'geeVector', 'strokeColor': 'ffffff', 'strokeWidth': 2,
     'fillColor': '00000000'},
    'McDonald-Dunn Study Area',
)

Map.setCenter(-123.34, 44.70, 11)
Map.view()
input('Section 11 recovery stage map open — press Enter to finish.')

print('\nAll sections complete.')
