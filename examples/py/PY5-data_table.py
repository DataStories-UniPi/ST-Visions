import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path.cwd().parent / ".env")
env = os.environ

import pandas as pd
import bokeh.models as bkhm
from st_visions.visualization.st_visualizer import st_visualizer

pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

# TO EXECUTE SCRIPT USE (ON REMOTE SERVER)
# python -m bokeh serve --show examples/py/PY5-data_table.py --allow-websocket-origin=<NODE_IP_ADDRESS>:<BOKEH_PORT>

# TO EXECUTE SCRIPT USE (ON LOCAL SERVER)
# python -m bokeh serve --show examples/py/PY5-data_table.py

data_points = st_visualizer(limit=5000) # Initialize a VISIONS Instance (ST Visualizer Object)
data_points.get_data_csv(filepath=env['NUMERICAL_SUBSET_DEMO'], nrows=10000)


tooltips = [('Vessel ID','@vessel_id'), ('Timestamp','@t'), ('Speed (knots)','@speed'),
            ('Course over Ground (degrees)','@course'), ('Heading (degrees)','@heading'), 
            ('Coordinates','(@lon, @lat)')]

data_points.create_canvas(title=f'Simple Visualization', tile_provider="CARTODBPOSITRON", sizing_mode='stretch_both', height=800, tools="pan, box_zoom, lasso_select, wheel_zoom, hover, save, reset")
circ = data_points.add_marker(marker='circle', size=10, color='royalblue', alpha=0.7, fill_alpha=0.5, muted_alpha=0, legend_label=f'Vessel GPS Locations')
data_points.add_hover_tooltips(tooltips)
data_points.add_lasso_select()


columns = [
        bkhm.TableColumn(field="t", title="Timestamp"),
        bkhm.TableColumn(field="vessel_id", title="Vessel ID"),
        bkhm.TableColumn(field="speed", title="Speed (knots)"),
        bkhm.TableColumn(field="heading", title="Heading"),
        bkhm.TableColumn(field="lon", title="Longitude"),
        bkhm.TableColumn(field="lat", title="Latitude"),
        bkhm.TableColumn(field="course", title="COG")
]
# data_table = bkhm.DataTable(source=data_points.source, columns=columns, width=400, height=280, sizing_mode='stretch_width')
data_table = bkhm.DataTable(source=data_points.source, columns=columns, width=400, height=280, sizing_mode='stretch_both')


### Camera, Lights, Action
data_points.figure.legend.location = "top_left"
data_points.figure.legend.click_policy = "mute"
data_points.figure.toolbar.active_scroll = data_points.figure.select_one(bkhm.WheelZoomTool)


#data_points.show_figures([[data_points.figure, data_table], [None, None]], width=1900, sizing_mode='stretch_both', notebook=False)
data_points.show_figures(
    figures=[data_points.figure, data_table],
    ncols=2,
    notebook=False,
    sizing_mode='stretch_both'
)


