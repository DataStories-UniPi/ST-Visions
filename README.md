# ST_Visions
### A Python-based library for interactive spatio-temporal data visualization.


## Overview
ST_Visions (**S**patio-**T**emporal **Vis**ualizat**ions**) is a python library, able to interactively visualize spatio-temporal data in a quick-and-easy way. Based upon the functionality of [Bokeh](https://docs.bokeh.org/en/latest/index.html#), and further extending it, we are able to create powerful and cohesive visualizations (and/or online dashboards), for large or streaming spatio-temporal datasets.

## Installation

ST_Visions has been configured to be installed as a package using pip. It is recommended to create a virtual Python environment before installing the library to avoid any dependency conflicts. Depending on your use-case, theres multiple ways to set up the library.

### Install as a package (recommended)
Installs all dependencies automatically:
```bash
pip install git+https://github.com/DataStories-UniPi/ST-Visions.git
```

### Developer Install
For contributing or modifying the source code:
```bash
git clone https://github.com/DataStories-UniPi/ST-Visions.git
cd st-visions
pip install -e .
```

### Manual Install
If you prefer to manage dependencies yourself:
```bash
git clone https://github.com/DataStories-UniPi/ST-Visions.git
cd st-visions

# Using pip/virtualenv
pip install −r requirements.txt
# Using conda
conda install --file requirements.txt
```
Then add the repo root to your path in your script or notebook:
```python
import sys
sys.path.append("/path/to/st-visions")
```

## Usage
ST_Visions can be used in two variations, depending on the use-case. For baseline visualizations, the module ```st_vizexpress.py``` provides 4 methods for visualizing Point, (Multi)Polygon, (Multi)Line datasets and data streams, respectively. For example, to visualize a Point geometry dataset:

* Using ```st_visualizer.py``` module: 

```Python
import pandas as pd
from st_visions.visualization.st_visualizer import st_visualizer

# Load Dataset (Pandas DataFrame)
data = pd.read_csv("<PATH-TO-CSV-FILE>")

# Create a ST_Visions Instance
plot = st_visualizer()

# Load the dataset into the instance
plot.set_data(data)

# Create the canvas of the instance
plot.create_canvas(title=f'Prototype Plot', tile_provider="CARTODBPOSITRON", sizing_mode='scale_width', height=540)

# Visualize the points to the canvas 
_ = plot.add_marker(marker='circle', size=10, color='royalblue', alpha=0.7, fill_alpha=0.6, muted_alpha=0, legend_label=f'Vessel GPS Locations')

# Set WheelZoomTool as the active scroll tool
plot.figure.toolbar.active_scroll = plot.figure.select_one(viz.WheelZoomTool)
```

* Using ```st_vizexpress.py``` module: 

```Python
import pandas as pd
from st_visions.visualization.st_visualizer import st_visualizer
import st_visions.express.st_vizexpress as viz_express

# Load Dataset (Pandas DataFrame)
data = pd.read_csv("<PATH-TO-CSV-FILE>")

# Create an ST_Visions Instance
plot = viz.st_visualizer()

# Load the dataset into the instance
plot.set_data(data)

# Visualize data on the map
viz_express.plot_points_on_map(plot)
```

ST_Visions can also be used to hook into a data stream and visualize the receiving data in real time using the ```st_vizstream.py``` module.

* Using the ```ST_KafkaStream``` subclass to subscribe to a Kafka topic
```Python

import pyarrow as pa
from st_visions.visualization.st_visualizer import st_visualizer 
from st_visions.streaming.st_vizstream import ST_KafkaStream 

# Initialize the schema we expect to receive from the data stream
expected_schema = pa.schema([
    ("lon", pa.float64()),
    ("lat", pa.float64()),
    ("vessel_id", pa.int64()),
    ("speed", pa.float32()),
    ("course", pa.float32()),
    ("heading", pa.float32()),
    ("t", pa.timestamp('ms'))
])

# Create an ST_Visions Instance
stream_plot = st_visualizer(limit=7500, expected_schema=expected_schema) 

# Prime the canvas to await the data stream 
stream_plot.create_canvas(
    title="Showing Streaming Data",
    tile_provider="CARTODBPOSITRON",
    sizing_mode='fixed',
    width=1600,
    height=800,
    tools="pan, box_zoom, lasso_select, wheel_zoom, hover, save, reset"
)

# Visualize the points to the canvas 
stream_plot.add_marker(
    marker='circle',
    size=10,
    color='royalblue',
    alpha=0.7,
    fill_alpha=0.5,
    muted_alpha=0,
    legend_label='Vessel GPS Locations'
)

# Create an ST_KafkaStream instance subscribed to your topic of choice
stream = ST_KafkaStream(topic_name='st-viz-topic')

# Hook into the data stream 
stream_plot.get_data_stream(stream=stream, notebook=False, refresh_rate=250)

# Set WheelZoomTool as the active scroll tool
stream_plot.figure.toolbar.active_scroll = plot.figure.select_one(viz.WheelZoomTool)

```

* Using ```st_vizexpress.py``` module

```Python

from st_visions.visualization.st_visualizer import st_visualizer
import st_visions.express.st_vizexpress as viz_express
import pyarrow as pa

# Initialize the schema we expect to receive from the data stream
expected_schema = pa.schema([
    ("lon", pa.float64()),
    ("lat", pa.float64()),
    ("vessel_id", pa.int64()),
    ("speed", pa.float32()),
    ("course", pa.float32()),
    ("heading", pa.float32()),
    ("t", pa.timestamp('ms'))
])

# Create an ST_Visions Instance
stream_plot = st_visualizer(limit=7500, expected_schema=expected_schema)

# Hook into the stream and visualize the ingested data
viz_express.plot_streaming_data_on_map_kafka(stream_plot, topic_name='st-viz-topic', tools=['lasso_select'], sizing_mode='fixed', width=1600, tooltips=tooltips)

```

Finally, to show our figure, the ```show_figures``` method is used. Depending on the use-case, figures can be visualized either within a Jupyter Notebook cell or a Browser Window (as a Python Script). In the case of a live stream, the ```live``` flag should be set to true when calling the ```show_figures``` method.

```Python
# Render on Jupyter Notebook; or
plot.show_figures(notebook=True, notebook_url='http://<NOTEBOOK_IP_ADDRESS>:<NOTEBOOK_PORT>')

# Render on Browser Window (via Python Script)
plot.show_figures(notebook=False)

# Plotting data received from a stream
plot.show_figures(notebook=False, live=True)
```

## Documentation
To learn more about ```ST_Visions``` and its capabilities, please consult the technical report at ```./doc/report.pdf```. Example codes that show both baseline and advanced use-cases, can be found at ```./examples/ipynb/``` for Jupyter Notebooks and ```./examples/py/``` for Python Scripts. Keep in mind that if ```ST_Visions``` was installed as a package, you will need to download the example folder seperately in order to access these examples.


## Contributors
Andreas Tritsarolis, Christos Doulkeridis, Yannis Theodoridis and Nikos Pelekis; Data Science Lab., University of Piraeus

Paraschos Moraitis, Department of Informatics, University of Piraeus

## Citation
If you use ST_Visions in your project, we would appreciate citations to the following paper:

> Andreas Tritsarolis, Christos Doulkeridis, Nikos Pelekis, and Yannis Theodoridis. 2021. ST_Visions: A Python Library for Interactive Visualization of Spatio-temporal Data. In Proceedings of the 22nd IEEE International Conference on Mobile Data Management (MDM). 

## Acknowledgement
This  project  has  received  funding  from  the  Hellenic Foundation for Research and Innovation (HFRI) and the General Secretariat for Research and Technology (GSRT), under grant agreement No 1667, from 2018 National Funds Programme of the GSRT, and from EU/H2020 project VesselAI (grant agreement No 957237).