import os, sys
import pandas as pd
import geopandas as gpd
import shapely
import datetime
import numpy as np
from tqdm import tqdm
from datetime import datetime

import bokeh as bkh
import bokeh.models as bkhm
import bokeh.palettes as bokeh_palettes
import bokeh.colors as bokeh_colors

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from st_visualizer import st_visualizer
import express as viz_express
import geom_helper as viz_helper
import callbacks


pd.set_option('display.expand_frame_repr', False)

pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)



df = pd.read_csv('./data/csv/ais_brest_jan_24.csv')


data_points = st_visualizer(limit=1000)
data_points.set_data(df)


tooltips = [('Vessel ID','@mmsi'), ('Timestamp','@ts'), ('Speed (knots)','@speed'),
            ('Course over Ground (degrees)','@course'), ('Heading (degrees)','@heading'), ('Coordinates','(@lon, @lat)')]

data_points.create_canvas(title=f'Prototype Plot', sizing_mode='stretch_both', plot_height=540, tools="pan,box_zoom,lasso_select,wheel_zoom,previewsave,reset,hover", tooltips=tooltips)
data_points.add_map_tile('CARTODBPOSITRON')

data_points.add_glyph(fill_alpha=0.6, muted_alpha=0, legend_label=f'GPS Locations (Choropleth Map)')


columns = [
        bkhm.TableColumn(field="mmsi", title="MMSI"),
        bkhm.TableColumn(field="status", title="Status"),
        bkhm.TableColumn(field="turn", title="Turn"),
        bkhm.TableColumn(field="speed", title="Speed"),
        bkhm.TableColumn(field="heading", title="Heading"),
        bkhm.TableColumn(field="lon", title="Longitude"),
        bkhm.TableColumn(field="lat", title="Latitude"),
        bkhm.TableColumn(field="ts", title="Timestamp"),
        bkhm.TableColumn(field="velocity", title="Velocity"),
        bkhm.TableColumn(field="course_over_ground", title="COG")
]
# data_table = bkhm.DataTable(source=data_points.source, columns=columns, width=400, height=280, sizing_mode='stretch_width')
data_table = bkhm.DataTable(source=data_points.source, columns=columns, width=400, height=280, sizing_mode='stretch_both')


### Camera, Lights, Action
data_points.figure.legend.location = "top_left"
data_points.figure.legend.click_policy = "mute"
data_points.figure.toolbar.active_scroll = data_points.figure.select_one(bkhm.WheelZoomTool)


data_points.show_figures([[data_points.figure, data_table], [None, None]], plot_width=1900, sizing_mode='stretch_both', notebook=False)


