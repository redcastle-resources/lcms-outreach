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



