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
import express as viz_express

# TO EXECUTE SCRIPT USE (ON REMOTE SERVER)
# python -m bokeh serve --show data/scripts/test2.py --allow-websocket-origin=<NODE_IP_ADDRESS>:<BOKEH_PORT>

# TO EXECUTE SCRIPT USE (ON LOCAL SERVER)
# python -m bokeh serve --show data/scripts/test2.py


st_viz = st_visualizer(limit=500)
st_viz.get_data_csv('./data/csv/ais_brest_2015-2016.csv', sp_columns=['lon', 'lat'], nrows=30000)


tooltips = [('Vessel ID','@mmsi'), ('Timestamp','@ts'), ('Speed (knots)','@speed'),('Course over Ground (degrees)','@course'), ('Heading (degrees)','@heading'), ('Coordinates','(@lon, @lat)')]
viz_express.plot_points_on_map(st_viz, tools=['hover,lasso_select'], tooltips=tooltips)

st_viz.add_numerical_filter(title='Speed (knots)', filter_mode='>=', numeric_name='speed', step=1, callback_policy='value')

st_viz.figure.legend.location = "top_left"
st_viz.figure.legend.click_policy = "mute"
st_viz.figure.toolbar.active_scroll = st_viz.figure.select_one(WheelZoomTool)


st_viz.show_figures(notebook=False)
