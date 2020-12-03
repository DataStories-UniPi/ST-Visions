import yaml

from datetime import date
import pandas as pd 

import bokeh.palettes as bokeh_palettes
import bokeh.models as bokeh_models

from bokeh.layouts import column, gridplot
from bokeh.models import ColumnDataSource, Slider, DateRangeSlider
from bokeh.plotting import figure, curdoc
from bokeh.themes import Theme
from bokeh.io import show, output_notebook, reset_output
from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import st_visualizer
import express as viz_express
import geom_helper as viz_helper

# TO EXECUTE SCRIPT USE (ON REMOTE SERVER)
# python -m bokeh serve --show data/scripts/test.py --allow-websocket-origin=<NODE_IP_ADDRESS>:<BOKEH_PORT>

# TO EXECUTE SCRIPT USE (ON LOCAL SERVER)
# python -m bokeh serve --show data/scripts/test.py


world_airports = pd.read_csv('./data/csv/world_airports.csv')
world_airports = world_airports.loc[world_airports.Altitude >= 0].copy()

world_airports = viz_helper.getGeoDataFrame_v2(world_airports, coordinate_columns=['Longitude', 'Latitude'], crs='epsg:4326')

''' For webmercator, when latitudes tend to 90 deg, northing tend to infinity, so using 89.9999 is not the solution. 
    The recommended area of use of EPSG:3857 is for latitudes between -85 and 85 degrees.
    Thus, we get the locations that reside anywhere but the poles. '''

world_airports = world_airports.loc[world_airports.Latitude.between(-85, 85)]



st_viz = st_visualizer.st_visualizer(limit=500)
st_viz.set_data(world_airports, sp_columns=['Longitude', 'Latitude'])

tooltips = [('Name','@Name'), ('City Country','@City_Country'), ('IATA','@IATA'), ('Location','(@Longitude, @Latitude, @Altitude)'), ('Timezone', '@Timezone.1')]
viz_express.plot_points_on_map(st_viz, tools=['hover,lasso_select'], tooltips=tooltips)

st_viz.add_categorical_filter()
st_viz.add_numerical_filter(filter_mode='>=', callback_policy='value_throttled')


st_viz.figure.legend.location = "top_left"
st_viz.figure.legend.click_policy = "mute"
st_viz.figure.toolbar.active_scroll = st_viz.figure.select_one(bokeh_models.WheelZoomTool)

st_viz.show_figures(notebook=False)
