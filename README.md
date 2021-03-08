# ST_Visions
### A Python-based library for interactive spatio-temporal data visualization.


## Overview
---
ST_Visions (**S**patio-**T**emporal **Vis**ualizat**ions**) is a python library, able to interactively visualize spatio-temporal data in a quick-and-easy way. Based upon the functionality of [Bokeh](https://docs.bokeh.org/en/latest/index.html#), and further extending it, we are able to create powerful and cohesive visualizations (and/or online dashboards), for large or streaming spatio-temporal datasets.


## Installation
---
In order to use ST_Visions in your project, download all necessary modules in your directory of choice via pip or conda, install the class’ dependencies, as the following commands suggest:

```Python
# Using pip/virtualenv
pip install −r requirements.txt

# Using conda
conda install --file requirements.txt
```


## Usage
---
ST_Visions can be used in two variations, depending on the use-case. For baseline visualizations, the module ```express.py``` provides 3 methods for visualizing Point, (Multi)Polygon and (Multi)Line datasets, respectively. For example, to visualize a Point geometry dataset:

* Using ```st_visualizer.py``` module: 

```Python
import pandas as pd
import st_visions.st_visualizer as viz

# Load Dataset (Pandas DataFrame)
data = pd.read_csv("<PATH-TO-CSV-FILE>")

# Create a ST_Visions Instance
plot = viz.st_visualizer()

# Load the dataset into the instance
plot.set_data(data)

# Create the canvas of the instance
plot.create_canvas(title=f'Prototype Plot', sizing_mode='scale_width', plot_height=540)

# Add a map tile to the instance
plot.add_map_tile('CARTODBPOSITRON')

# Visualize the points to the canvas 
_ = plot.add_glyph(glyph_type='circle', size=10, color='royalblue', alpha=0.7, fill_alpha=0.6, muted_alpha=0, legend_label=f'Vessel GPS Locations')

# Set WheelZoomTool as the active scroll tool
plot.figure.toolbar.active_scroll = plot.figure.select_one(viz.WheelZoomTool)
```

* Using ```express.py``` module: 

```Python
import pandas as pd
import st_visions.st_visualizer as viz
import st_visions.express as viz_express

# Load Dataset (Pandas DataFrame)
data = pd.read_csv("<PATH-TO-CSV-FILE>")

# Create a ST_Visions Instance
plot = viz.st_visualizer()

# Load the dataset into the instance
plot.set_data(data)

# Visualize data on the map
viz_express.plot_points_on_map(plot)
```

Finally, to show our figure, the ```show_figures``` method is used. Depending on the use-case, figures can be visualized either within a Jupyter Notebook cell or a Browser Window (as a Python Script).

```Python
# Render on Jupyter Notebook; or
plot.show_figures(notebook=True, notebook_url='http://<NOTEBOOK_IP_ADDRESS>:<NOTEBOOK_PORT>')

# Render on Browser Window (via Python Script)
plot.show_figures(notebook=False)
```

## Documentation
---
To learn more about ```ST_Visions``` and its capabilities, please consult the technical report at ```./doc/report.pdf```. Example codes that show both baseline and advanced use-cases, can be found at ```./examples/ipynb/``` for Jupyter Notebooks and ```./examples/py/``` for Python Scripts.


## Contributors
---
Andreas Tritsarolis, Christos Doulkeridis, Yannis Theodoridis and Nikos Pelekis; Data Science Lab., University of Piraeus


## Acknowledgement
---
This  project  has  received  funding  from  the  Hellenic Foundation for Research and Innovation (HFRI) and the General Secretariat for Research and Technology (GSRT), under grant agreement No 1667, from 2018 National Funds Programme of the GSRT, and from EU/H2020 project VesselAI (grant agreement No 957237).