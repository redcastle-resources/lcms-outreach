# HJ Andrews Harvest Recovery Analysis - Script only 

# Load libraries
import ee
import os
# EE setup
EE_PROJECT = 'mercer-eudr-training' # replace with your GEE Cloud project ID
ee.Authenticate() # only need to run this once
ee.Initialize(project=EE_PROJECT) # replace with your GEE Cloud project ID
import geeViz.getImagesLib as gil
import geeViz.geeView
geeViz.geeView.project_id = EE_PROJECT

# Test that EE worked
img = ee.Image(1)
print(img.getInfo())

# Load LCMS asset for metadata
lcms_for_metadata = ee.ImageCollection('USFS/GTAC/LCMS/v2024-10')
lcms_props = lcms_for_metadata.first().toDictionary().getInfo()

# keep only the class dicts; we don't want to keep version-specific properties
lcms_props = {k: v for k, v in lcms_props.items() if "class" in k}

# write out properties to local file to use for 2025-11 products
write_path = os.path.join(os.getcwd(), 'data/lcms_metadata.json')
with open(write_path, 'w') as f:
    import json
    json.dump(lcms_props, f, indent=4)




