import pyarrow as pa
import bokeh.models as bokeh_models

from st_visions.visualization.st_visualizer import st_visualizer
from st_visions.streaming.st_vizstream import ST_KafkaStream


# TO EXECUTE SCRIPT USE (ON REMOTE SERVER)
# python -m bokeh serve --show examples/py/PY6a-streaming.py --allow-websocket-origin=<NODE_IP_ADDRESS>:<BOKEH_PORT>

# TO EXECUTE SCRIPT USE (ON LOCAL SERVER)
# python -m bokeh serve --show examples/py/PY6a-streaming.py

expected_schema = pa.schema([
    ("lon", pa.float64()),
    ("lat", pa.float64()),
    ("vessel_id", pa.int64()),
    ("speed", pa.float32()),
    ("course", pa.float32()),
    ("heading", pa.float32()),
    ("t", pa.timestamp('ms'))
])

st_viz = st_visualizer(limit=7500, expected_schema=expected_schema)

st_viz.create_canvas(
    title="Showing Streaming Data",
    tile_provider="CARTODBPOSITRON",
    sizing_mode='fixed',
    width=1600,
    height=800,
    tools="pan, box_zoom, lasso_select, wheel_zoom, hover, save, reset"
)

st_viz.add_marker(
    marker='circle',
    size=10,
    color='royalblue',
    alpha=0.7,
    fill_alpha=0.5,
    muted_alpha=0,
    legend_label='Vessel GPS Locations'
)

# use your own topic or name your topic 'st-viz-topic'
stream = ST_KafkaStream(topic_name='st-viz-topic')
st_viz.get_data_stream(stream=stream, notebook=False, refresh_rate=250)


tooltips = [
    ('Vessel ID','@vessel_id'),
    ('Timestamp','@t'),
    ('Speed (knots)','@speed'),
    ('Course over Ground (degrees)','@course'),
    ('Heading (degrees)','@heading'),
    ('Coordinates','(@lon_merc, @lat_merc)')
]
st_viz.add_hover_tooltips(tooltips)
st_viz.add_lasso_select()
st_viz.figure.legend.location = "top_left"
st_viz.figure.legend.click_policy = "mute"
st_viz.figure.toolbar.active_scroll = st_viz.figure.select_one(bokeh_models.WheelZoomTool)

st_viz.show_figures(notebook=False, live=True, sizing_mode='stretch_both')