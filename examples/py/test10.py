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



### Loading GeoLife Dataset
gdf = pd.read_csv('./data/csv/geolife_trips_cleaned_v2_china_subset.csv', nrows=50000)
gdf = viz_helper.getGeoDataFrame_v2(gdf, crs='epsg:4326')

### Creating Choropleth (Grid) Geometry
bbox = np.array(gdf.total_bounds)

p1 = shapely.geometry.Point(bbox[0], bbox[3])
p2 = shapely.geometry.Point(bbox[2], bbox[3])
p3 = shapely.geometry.Point(bbox[2], bbox[1])
p4 = shapely.geometry.Point(bbox[0], bbox[1])

np1 = (p1.coords.xy[0][0], p1.coords.xy[1][0])
np2 = (p2.coords.xy[0][0], p2.coords.xy[1][0])
np3 = (p3.coords.xy[0][0], p3.coords.xy[1][0])
np4 = (p4.coords.xy[0][0], p4.coords.xy[1][0])

spatial_coverage = gpd.GeoDataFrame(gpd.GeoSeries(shapely.geometry.Polygon([np1, np2, np3, np4])), columns=['geom'], geometry='geom',  crs='epsg:4326')
spatial_coverage_cut = viz_helper.quadrat_cut_geometry(spatial_coverage, 0.7)
spatial_coverage_cut = gpd.GeoDataFrame(np.array(list(spatial_coverage_cut)).reshape(-1,1), geometry=0, crs='epsg:4326')


### Classifying Area Proximity (i.e., Populate the Choropleth Map)
cnt = viz_helper.classify_area_proximity(gdf.copy(), spatial_coverage_cut, compensate=True, verbose=True).area_id.value_counts()

spatial_coverage_cut.loc[cnt.index, 'count'] = cnt.values
spatial_coverage_cut.rename({0:'geom'}, axis=1, inplace=True)
spatial_coverage_cut.set_geometry('geom', inplace=True)



st_viz = st_visualizer(limit=len(spatial_coverage_cut))
st_viz.set_data(spatial_coverage_cut)

st_viz.create_canvas(title=f'Prototype Plot', sizing_mode='scale_width', plot_height=540, tools="pan,box_zoom,lasso_select,wheel_zoom,previewsave,reset")
st_viz.add_map_tile('CARTODBPOSITRON')

st_viz.add_numerical_colormap('Viridis256', 'count', colorbar=True, cb_orientation='vertical', cb_location='right', label_standoff=12, border_line_color=None, location=(0,0), nan_color=bokeh_colors.RGB(1,1,1,0))
st_viz.add_polygon(fill_color=st_viz.cmap, line_color=st_viz.cmap, fill_alpha=0.6, muted_alpha=0, legend_label=f'GPS Locations (Choropleth)')



data_points = st_visualizer(limit=len(gdf))
data_points.set_data(gdf)
data_points.set_figure(st_viz.figure)


categorical_name='label'

class Callback(callbacks.BokehFilters):
    def __init__(self, vsn_instance, widget):
        super().__init__(vsn_instance, widget)
        
        
    def callback_prepare_data(self, new_pts, ready_for_output):
        self.vsn_instance.canvas_data = new_pts

        if ready_for_output:
            cnt = viz_helper.classify_area_proximity(self.vsn_instance.canvas_data, st_viz.data, compensate=True, verbose=True).area_id.value_counts()            
            st_viz.canvas_data = st_viz.data.loc[cnt.index].copy()
            st_viz.canvas_data.loc[:, 'count'] = cnt.values               
           
            st_viz.canvas_data = st_viz.prepare_data(st_viz.canvas_data)

            low, high = st_viz.canvas_data[st_viz.cmap['field']].agg([np.min, np.max])
            st_viz.cmap['transform'].low = 0 if low == high else low
            st_viz.cmap['transform'].high = high
                    
            st_viz.source.data = st_viz.canvas_data.drop(st_viz.canvas_data.geometry.name, axis=1).to_dict(orient="list")

            # print ('Releasing Lock...')
            st_viz.canvas_data = None
            self.vsn_instance.canvas_data = None
            self.vsn_instance.aquire_canvas_data = None
        
        
    def callback(self, attr, old, new):
        self.callback_filter_data()

        cat_value = self.widget.value
        new_pts = self.get_data()

        # print (cat_value, categorical_name)
        if cat_value:
            new_pts = new_pts.loc[new_pts[categorical_name] == cat_value].copy()

        self.callback_prepare_data(new_pts, self.widget.id==self.vsn_instance.aquire_canvas_data)

        
data_points.add_categorical_filter(title='Vehicle', categorical_name=categorical_name, height_policy='min', callback_class=Callback)


### Camera, Lights, Action
data_points.figure.legend.location = "top_left"
data_points.figure.legend.click_policy = "mute"
data_points.figure.toolbar.active_scroll = data_points.figure.select_one(bkhm.WheelZoomTool)


data_points.show_figures(notebook=False)


