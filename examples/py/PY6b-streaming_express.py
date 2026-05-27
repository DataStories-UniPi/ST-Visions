import pyarrow as pa
from st_visions.visualization.st_visualizer import st_visualizer
import st_visions.express.st_vizexpress as st_express

# TO EXECUTE SCRIPT USE (ON REMOTE SERVER)
# python -m bokeh serve --show examples/py/PY6b-streaming_express.py --allow-websocket-origin=<NODE_IP_ADDRESS>:<BOKEH_PORT>

# TO EXECUTE SCRIPT USE (ON LOCAL SERVER)
# python -m bokeh serve --show examples/py/PY6b-streaming_express.py


expected_schema = pa.schema([
    ("lon", pa.float64()),
    ("lat", pa.float64()),
    ("vessel_id", pa.int64()),
    ("speed", pa.float32()),
    ("course", pa.float32()),
    ("heading", pa.float32()),
    ("t", pa.timestamp('ms'))
])

tooltips = [
    ('Vessel ID','@vessel_id'),
    ('Timestamp','@t'),
    ('Speed (knots)','@speed'),
    ('Course over Ground (degrees)','@course'),
    ('Heading (degrees)','@heading'),
    ('Coordinates','(@lon_merc, @lat_merc)')
]

st_viz = st_visualizer(limit=5000, expected_schema=expected_schema)
st_express.plot_streaming_data_on_map_kafka(st_viz, tools=['lasso_select'], sizing_mode='fixed', width=1600, tooltips=tooltips)
st_viz.show_figures(notebook=False, live=True, sizing_mode='stretch_both')




