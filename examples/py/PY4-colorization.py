import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path.cwd().parent / ".env")
env = os.environ

import bokeh.models as bokeh_models
from st_visions.visualization.st_visualizer import st_visualizer

# TO EXECUTE SCRIPT USE (ON REMOTE SERVER)
# python -m bokeh serve --show examples/py/PY4-colorization.py --allow-websocket-origin=<NODE_IP_ADDRESS>:<BOKEH_PORT>

# TO EXECUTE SCRIPT USE (ON LOCAL SERVER)
# python -m bokeh serve --show examples/py/PY4-colorization.py


st_viz = st_visualizer(limit=20000) # Initialize a VISIONS Instance (ST Visualizer Object)
st_viz.get_data_csv(filepath=env['NUMERICAL_SUBSET_DEMO'], nrows=100000)

st_viz.create_canvas(title=f'Prototype Plot', sizing_mode='fixed', height=800, width=1600, tools="pan, box_zoom, lasso_select, wheel_zoom, hover, save, reset")

st_viz.add_numerical_colormap('Viridis256', 'speed', colorbar=True, cb_orientation='vertical', cb_location='right', label_standoff=12, border_line_color=None, location=(0,0))
st_viz.add_marker(marker='circle', size=8, color=st_viz.cmap, alpha=0.8, fill_alpha=0.7, muted_alpha=0, legend_label=f'GPS Locations (Speed Heatmap)')
#st_viz.add_temporal_filter(temporal_name='t', temporal_unit='ms', step_ms=15000, title='Temporal Horizon', callback_policy='value_throttled')
st_viz.add_temporal_filter(
    temporal_name='t',
    temporal_unit='ms',
    step_ms=int(28800000/8),
    start_date=pd.Timestamp('2017-11-30 00:00:00'),
    end_date=pd.Timestamp('2017-12-01 18:00:00'),
    title='Temporal Horizon',
    callback_policy='value_throttled',
    width=1200
)

tooltips = [('Vessel ID','@vessel_id'), ('Timestamp','@t'), ('Speed (knots)','@speed'),('Course over Ground (degrees)','@course'), ('Heading (degrees)','@heading'), ('Coordinates','(@lon, @lat)')]
st_viz.add_hover_tooltips(tooltips)
st_viz.add_lasso_select()

st_viz.figure.legend.location = "top_left"
st_viz.figure.legend.click_policy = "mute"
st_viz.figure.toolbar.active_scroll = st_viz.figure.select_one(bokeh_models.WheelZoomTool)

st_viz.show_figures(notebook=False, sizing_mode='stretch_both')