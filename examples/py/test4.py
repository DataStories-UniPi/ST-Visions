import yaml

from datetime import date
import pandas as pd 
import geopandas as gpd 

from bokeh.layouts import column, gridplot
from bokeh.models import ColumnDataSource, Slider, DateRangeSlider, WheelZoomTool
from bokeh.plotting import figure, curdoc
from bokeh.themes import Theme
from bokeh.io import show, output_notebook, reset_output

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from st_visualizer import *

# TO EXECUTE SCRIPT USE (ON REMOTE SERVER)
# python -m bokeh serve --show data/scripts/test2.py --allow-websocket-origin=<NODE_IP_ADDRESS>:<BOKEH_PORT>

# TO EXECUTE SCRIPT USE (ON LOCAL SERVER)
# python -m bokeh serve --show data/scripts/test2.py


st_viz = st_visualizer(limit=500)
st_viz.get_data_csv(filepath='./data/csv/ais_brest_2015-2016.csv', nrows=30000)

st_viz.create_canvas(title=f'Prototype Plot', sizing_mode='stretch_both', plot_width=800, plot_height=600)

st_viz.add_map_tile('CARTODBPOSITRON')
_ = st_viz.add_glyph(glyph_type='circle', size=10, color='royalblue', alpha=0.7, fill_alpha=0.5, muted_alpha=0, legend_label=f'Vessel GPS Locations')

tooltips = [('Vessel ID','@mmsi'), ('Timestamp','@ts'), ('Speed (knots)','@speed'),('Course over Ground (degrees)','@course'), ('Heading (degrees)','@heading'), ('Coordinates','(@lon, @lat)')]
st_viz.add_hover_tooltips(tooltips)
st_viz.add_lasso_select()

st_viz.figure.legend.location = "top_left"
st_viz.figure.legend.click_policy = "mute"
st_viz.figure.toolbar.active_scroll = st_viz.figure.select_one(WheelZoomTool)

st_viz.add_temporal_filter(width_policy='fit', step_ms=500, width=800)

st_viz.show_figures(notebook=False)
