import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path.cwd().parent / ".env")
env = os.environ

from bokeh.models import WheelZoomTool
from st_visions.visualization.st_visualizer import st_visualizer
import st_visions.express.st_vizexpress as viz_express


# TO EXECUTE SCRIPT USE (ON REMOTE SERVER)
# python -m bokeh serve --show examples/py/PY2-numerical_filter.py --allow-websocket-origin=<NODE_IP_ADDRESS>:<BOKEH_PORT>

# TO EXECUTE SCRIPT USE (ON LOCAL SERVER)
# python -m bokeh serve --show examples/py/PY2-numerical_filter.py

st_viz = st_visualizer(limit=5000) # Initialize a VISIONS Instance (ST Visualizer Object)
st_viz.get_data_csv(filepath=env['NUMERICAL_SUBSET_DEMO'], nrows=10000)


tooltips = [('Vessel ID','@vessel_id'), ('Timestamp','@t'), ('Speed (knots)','@speed'),
            ('Course over Ground (degrees)','@course'), ('Heading (degrees)','@heading'), ('Coordinates','(@lon, @lat)')]

viz_express.plot_points_on_map(st_viz, tools=['hover,lasso_select'], sizing_mode='fixed', tooltips=tooltips, width=1600)

st_viz.add_numerical_filter(title='Speed (knots)', filter_mode='>=', numeric_name='speed', step=1, callback_policy='value')

st_viz.figure.legend.location = "top_left"
st_viz.figure.legend.click_policy = "mute"
st_viz.figure.toolbar.active_scroll = st_viz.figure.select_one(WheelZoomTool)

st_viz.show_figures(notebook=False)
