'''
	st_visualizer.py - v2020.05.12

	Authors: Andreas Tritsarolis, Christos Doulkeridis, Yannis Theodoridis and Nikos Pelekis
'''


import sys, os
import operator
import numpy as np
import pandas as pd
import geopandas as gpd
from tqdm import tqdm

import bokeh
import bokeh.io as bokeh_io
import bokeh.plotting as bokeh_plt
import bokeh.models as bokeh_mdl
import bokeh.palettes as palettes

from bokeh.tile_providers import get_provider, Vendors
from bokeh.plotting import figure, output_file, reset_output, output_notebook, save, show
from bokeh.models import ColumnDataSource, CDSView, HoverTool, WheelZoomTool, GroupFilter, BooleanFilter, CustomJS, Slider, DateSlider
from bokeh.layouts import column, widgetbox, row

# Importing Helper Libraries
import geom_helper
import callbacks


# Defining Allowed Values (per use-case)
ALLOWED_BASIC_GLYPH_TYPES = ["asterisk", "circle", "circle_cross", "circle_x", "cross", "dash", 'diamond', 'diamond_cross', 'hex', "inverted_triangle", 'square', 'square_cross', 'square_x', 'triangle']
ALLOWED_BASIC_POLYGON_TYPES = ['multi_polygons', 'patches']
ALLOWED_BASIC_LINE_TYPES = ['hline_stack', 'line', 'multi_line', 'step', 'vline_stack']
ALLOWED_FILTER_OPERATORS = {'==': operator.eq, '!=': operator.ne, '<': operator.lt, '<=': operator.le, '>': operator.gt, '>=': operator.ge, 'range': None}
ALLOWED_CATEGORICAL_COLOR_PALLETES = ['Accent', 'Blues', 'BrBG', 'BuGn', 'Category10', 'Category20', 'Category20b', 'Category20c', 'Cividis', 'Colorblind', 'Dark2', 'GnBu', 'Greens', 'Greys', 'Inferno', 'Magma','OrRd', 'Oranges', 'PRGn', 'Paired', 'Pastel1', 'Pastel2', 'PiYG', 'Plasma', 'PuBu', 'PuBuGn', 'PuOr', 'PuRd', 'Purples', 'RdBu', 'RdGy', 'RdPu', 'RdYlBu', 'RdYlGn', 'Reds', 'Set1', 'Set2', 'Set3', 'Spectral', 'Turbo', 'Viridis', 'YlGn', 'YlGnBu', 'YlOrBr', 'YlOrRd']
ALLOWED_NUMERICAL_COLOR_PALETTES = ['Blues256', 'Greens256', 'Greys256', 'Inferno256', 'Magma256', 'Plasma256', 'Viridis256', 'Cividis256', 'Turbo256', 'Oranges256', 'Purples256', 'Reds256']


class st_visualizer:
    def __init__(self, limit=30000, allow_complex_geometries=False, proj='epsg:3857'):
        """
        Constructor for creating a VISIONS Instance.
            
        Parameters
        ----------
        limit: int (default: 30000)
            The maximum number of geometries (glyphs/polygons/lines) to be visualized.
        allow_complex_geometries: boolean (default: False)
            Choose to plot either the polygons' exterior (False) or along with its inner voids (True)
        proj: str (default: ```'epsg:3857'```)
            The CRS that the input geometries will be projected to prior to visualization.
        """
        self.limit = limit
        self.allow_complex_geometries = allow_complex_geometries
        self.proj = proj

        self.data = None
        self.canvas_data = None
        self.sp_columns = None
        
        self.figure = None
        self.source = None

        self.renderers = []
        self.widgets   = []

        self.cmap = None
        self.__suffix = None
        self.aquire_canvas_data = None
    

    def __set_data(self, data, columns):
        """
        Private Method for Saving the Dataset to the instance's attributes, along with the location of spatial coordinates.
            
        Parameters
        ----------
        data: GeoPandas GeoDataFrame
            The instance's loaded data
        columns: List 
            The (ordered) column names for the location of the spatial coordinates.
        """
        data = data.to_crs(self.proj)

        self.data = data
        self.sp_columns = columns


    def set_data(self, data, sp_columns=['lon', 'lat'], crs='epsg:4326'):
        """
        Loading a Dataset to a VISIONS instance.
            
        Parameters
        ----------
        data: Pandas DataFrame or GeoPandas GeoDataFrame
            The Dataset that will be loaded to the instance
        sp_columns: List (default: ```['lon', 'lat']```)
            The (ordered) column names for the location of the spatial coordinates.
        crs: str (default: ```'epsg:4326'```) 
            The CRS of the Dataset's spatial coordinates
        """
        if type(data) not in [type(gpd.GeoDataFrame()), type(pd.DataFrame())]:
            raise ValueError('"data" must be either a Pandas DataFrame or a GeoPandas GeoDataFrame')

        if type(data) != type(gpd.GeoDataFrame()):
            data = geom_helper.getGeoDataFrame_v2(data, coordinate_columns=sp_columns, crs=crs)
        
        self.__set_data(data, sp_columns)              


    def set_figure(self, figure=None):
        """
        Load a Canvas to the class' attributes
            
        Parameters
        ----------
        figure: bokeh.plotting.figure instance (default:None)
            The canvas in which the data will be drawn to.
        """
        self.figure = figure


    def set_source(self, source=None):
        """
        Load a CDS to the class' attributes
            
        Parameters
        ----------
        figure: bokeh.models.ColumnDataSource instance (default:None)
            The communication 'bridge' that will send data from the loaded dataset to the Canvas.
        """
        self.source = source


    def get_data_csv(self, filepath, sp_columns=['lon', 'lat'], crs='epsg:4326', **kwargs):
        """
        Parse a CSV file as a GeoDataFrame.
            
        Parameters
        ----------
        filepath: str
            The path to the CSV source file
        sp_columns: List (default: ```['lon', 'lat']```)
            The (ordered) list of columns that contain the spatial coordinates
        crs: str (default: ```'epsg:4326'```)  
            The CRS of the Dataset's spatial coordinates
        **kwargs: Dict
            Other arguments related to parsing a CSV file (consult pandas.read_csv method)
        """
        data = pd.read_csv(filepath, **kwargs)
        data = geom_helper.getGeoDataFrame_v2(data, coordinate_columns=sp_columns, crs=crs)
       
        self.__set_data(data, sp_columns)


    def get_data_postgres(self, sql, con, postgis=True, sp_columns=['lon', 'lat'], crs=None, **kwargs):
        """
        Parse a PostGIS SQL Result as a GeoDataFrame.
            
        Parameters
        ----------
        sql: str
            The SQL query for fetching the spatial data.
        sp_columns: List (default: ```['lon', 'lat']```)
            The (ordered) list of columns that contain the spatial coordinates
        crs: str (default: ```'epsg:4326'```)  
            The CRS of the Dataset's spatial coordinates
        **kwargs: Dict
            Other arguments related to parsing the SQL Result (consult geopandas.read_postgis method)
        """
        if postgis:
            data = gpd.read_postgis(sql, con, crs=crs, **kwargs)
        else:
            data = pd.read_sql_query(sql, con, **kwargs)
            data = geom_helper.getGeoDataFrame_v2(data, coordinate_columns=sp_columns, crs=crs)

        self.__set_data(data, sp_columns)


    def prepare_data(self, data=None, suffix=None):
        """
        Prepare the (loaded) data prior to rendering. 

        Parameters
        ----------
        data: GeoPandas GeoDataFrame (default:None)
            Prepare either the loaded data (None) or another DataFrame
        suffix: str (default: None)
            A suffix for the column name of the extracted spatial coordinates


        Returns
        -------
        GeoPandas GeoDataFrame
        """
        if data is None:
            data = self.data.copy()
        
        data = data.iloc[:self.limit].copy()
        
        if suffix is None:
            suffix = self.__suffix
        
        if (suffix is None or data is None):
            raise ValueError('You must either set a Dataset and/or set a Column suffix for extracted geometry coordinates.')
        
        for dim, coord_name in enumerate(self.sp_columns):
            data.loc[:, f'{coord_name}{suffix}'] = data.geometry.apply(lambda l: geom_helper.getCoords(l, dim, self.allow_complex_geometries))

        # print (data.head())
        return data
 

    def create_source(self, suffix='_merc'):
        """
        Create the instance's CDS.

        Parameters
        ----------
        suffix: str (default: ```'_merc'```)
            A suffix for the column name of the extracted spatial coordinates
        """
        if self.data is None:
            raise ValueError('You must set a DataFrame first.')

        # data_merc = self.data.iloc[:self.limit if limit is None else limit].copy()
        data_merc = self.prepare_data(suffix=suffix)

        source = ColumnDataSource(data_merc.drop([data_merc.geometry.name], axis=1))        
        # print (source.to_df())

        self.set_source(source)
        self.__suffix = suffix


    def create_canvas(self, title, x_range=None, y_range=None, suffix='_merc', **kwargs):        
        """
        Create the instance's Canvas and CDS.

        Parameters
        ----------
        title: str
            The Canvas' title. If the limit set at the constructor is less than the length of the loaded data, the title will be suffixed by ``` - Showing {self.limit} out of {len(self.data)} records'```
        x_range: NumPy Array
            The Canvas' spatial horizon at the longitude dimension
        y_range: Numpy Array
            The Canvas' spatial horizon at the latitude dimension
        suffix: str (default: ```'_merc'```)
            A suffix for the column name of the extracted spatial coordinates
        **kwargs: Dict
            Other arguments related to creating the instance's Canvas (consult bokeh.plotting.figure method)
        """
        if self.data is None:
            raise ValueError('You must set a DataFrame first.')
        
        if self.limit < len(self.data):
            title = f'{title} - Showing {self.limit} out of {len(self.data)} records'

        bbox = self.data.total_bounds
        if x_range is None:
            x_range=(np.floor(bbox[0]), np.ceil(bbox[2]))
        if y_range is None:
            y_range=(np.floor(bbox[1]), np.ceil(bbox[3]))

        fig = figure(x_range=x_range, y_range=y_range, x_axis_type="mercator", y_axis_type="mercator", title=title, **kwargs)
        
        self.set_figure(fig)   
        
        if self.source is None:
            self.create_source(suffix)
           

    def add_categorical_colormap(self, palette, categorical_name, **kwargs):
        """
        Create a Categorical Colormap 
            
        Parameters
        ----------
        palette: str or Tuple 
            The color palette of the colormap. It can either be one of Bokeh's default palettes or a Tuple of colors in hexadecimal format.
        categorical_name: str 
            The column name of the loaded dataset that contains the categorical values
        
        Returns
        -------
        cmap: Dict
            The Categorical Colormap 
        """
        if not (isinstance(palette, tuple) or palette in ALLOWED_CATEGORICAL_COLOR_PALLETES):
            raise ValueError(f'Invalid Palette Name/Tuple. Allowed (pre-built) Palettes: {ALLOWED_CATEGORICAL_COLOR_PALLETES}')

        categories = sorted(np.unique(self.source.data[categorical_name]).tolist())
        palette = palette if isinstance(palette, tuple) else getattr(palettes, palette)[len(categories)]

        # print(categories)
        cmap = bokeh_mdl.CategoricalColorMapper(palette=palette, factors=categories, **kwargs)

        # self.cmap = {'type':'add_categorical_colormap', 'cmap':{'field': categorical_name, 'transform': cmap}}
        self.cmap = {'field': categorical_name, 'transform': cmap}
        return self.cmap

    
    def add_numerical_colormap(self, palette, numeric_name, nan_color='gray', colorbar=True, cb_orientation='vertical', cb_location='right', label_standoff=12, border_line_color=None, location=(0,0), **kwargs): 
        """
        Create a Numerical Colormap.
            
        Parameters
        ----------
        palette: str or Tuple 
            The color palette of the colormap. It can either be one of Bokeh's default palettes or a Tuple of colors in hexadecimal format.
        numeric_name: str 
            The column name of the loaded dataset that contains the numerical values
        nan_color: str or bokeh.colors instance (default: ```'gray'```)
            The color name for the geometries that are outside the range of the colormap
        colorbar: boolean (default: True)
            Draw a colorbar alongside the Canvas
        cb_orientation: str (either ```'vertical'```, ```'horizontal'```)
            The orientation of the colorbar
        cb_location: str (either ```'left'```, ```'right'```, ```'above'```, ```'below'```)
            The location of the colorbar relative to the Canvas
        label_standoff: int (default: 12)
            The distance (in pixels) to separate the tick labels from the color bar.
        border_line_color: str or bokeh.colors instance (default: None)
            The color of the border of the colorbar        
        location: Tuple (int, int)
            Adjust the colorbar location relative to ```cb_orientation``` and ```cb_location```
        **kwargs: Dict
            Other aarguments related to the creation of the colorbar
        
        Returns
        -------
        cmap: Dict
            The Numerical Colormap 
        """
        if palette not in ALLOWED_NUMERICAL_COLOR_PALETTES:
            raise ValueError(f'Invalid Palette Name. Allowed (pre-built) Palettes: {ALLOWED_NUMERICAL_COLOR_PALETTES}')

        min_val, max_val = self.data[numeric_name].agg([np.min, np.max])
        cmap = bokeh_mdl.LinearColorMapper(palette=getattr(palettes, palette), low=min_val, high=max_val, nan_color=nan_color)
        
        if colorbar:
            cbar = bokeh_mdl.ColorBar(orientation=cb_orientation, color_mapper=cmap, label_standoff=label_standoff, border_line_color=border_line_color, location=location, **kwargs) # Other Params: height=height, width=width
            self.figure.add_layout(cbar, cb_location)

        # self.cmap = {'type':'add_numerical_colormap', 'cmap':{'field': numeric_name, 'transform': cmap}}
        self.cmap = {'field': numeric_name, 'transform': cmap}
        return self.cmap


    def add_glyph(self, glyph_type='circle', size=10, color='royalblue', sec_color='lightslategray', alpha=0.7, muted_alpha=0, **kwargs):
        """
        Add a Glyph to the Canvas
            
        Parameters
        ----------
        glyph_type: str (default: ```'circle'```)
            The Glyph's type
        size: int (default: 10)
            The Glyph's size
        color: str or bokeh.colors instance (default: ```'royalblue'```)
            The Glyph's primary color
        sec_color: str or bokeh.colors instance (default: ```'lightslategray'```)
            The Glyph's secondary color (i.e., the glyph's color when disselected).        
        alpha:float (values in [0,1] -- default: ```0.7```)
            The Glyph's overall alpha
        muted_alpha:float (values in [0,1] -- default: ```0```)
            The Glyph's alpha when disabled from the legend
        **kwargs: Dict
            Other arguments related to the creation of a Glyph
        
        Returns
        -------
        renderer: Bokeh glyph instance
            The instance of the added glyph
        """
        if glyph_type not in ALLOWED_BASIC_GLYPH_TYPES:
            raise ValueError(f'glyph_type must be one of the following: {ALLOWED_BASIC_GLYPH_TYPES}')

        coordinates = [f'{col}{self.__suffix}' for col in self.sp_columns]

        renderer = getattr(self.figure, glyph_type)(*coordinates, size=size, color=color, nonselection_fill_color=sec_color, alpha=alpha, muted_alpha=muted_alpha, source=self.source, **kwargs)
        self.renderers.append(renderer)

        return renderer

    
    def add_line(self, line_type='multi_line', line_color="royalblue", line_width=5, alpha=0.7, muted_alpha=0, **kwargs):
        """
        Add a PolyLine to the Canvas
            
        Parameters
        ----------
        line_type: str (default: ```'multi_line'```)
            The PolyLine's type
        line_color: str or bokeh.colors instance (default: ```'royalblue'```)
            The PolyLine's primary color
        line_width: int (default: 5)
            The Polyline's line width
        alpha:float (values in [0,1] -- default: ```0.7```)
            The PolyLine's alpha
        muted_alpha:float (values in [0,1] -- default: ```0```)
            The Polyline's alpha when disabled from the legend
        **kwargs: Dict
            Other arguments related to the creation of a PolyLine
        
        Returns
        -------
        renderer: Bokeh PolyLine instance
            The instance of the added PolyLine
        """
        if line_type not in ALLOWED_BASIC_LINE_TYPES:
            raise ValueError(f'line_type must be one of the following: {ALLOWED_BASIC_LINE_TYPES}')

        coordinates = [f'{col}{self.__suffix}' for col in self.sp_columns]

        renderer = getattr(self.figure, line_type)(*coordinates, source=self.source, line_color=line_color, line_width=line_width, alpha=alpha, muted_alpha=muted_alpha, **kwargs)
        self.renderers.append(renderer)

        return renderer


    def add_polygon(self, polygon_type='patches', line_width=1, line_color='royalblue', fill_color='royalblue', sec_color='lightslategray', fill_alpha=0.5, muted_alpha=0, **kwargs):
        """
        Add a Polygon to the Canvas
            
        Parameters
        ----------
        polygon_type: str (default: ```'patches'```)
            The Polygon's type

        line_width: int (default: 10)
            The Polygon's border line width

        line_color: str or bokeh.colors instance (default: ```'royalblue'```)
            The Polygon's border line color

        fill_color: str or bokeh.colors instance (default: ```'royalblue'```)
            The Polygon's fill color

        sec_color: str or bokeh.colors instance (default: ```'lightslategray'```)
            The Polygon's secondary color (i.e., the polygon's color when disselected).  

        fill_alpha:float (values in [0,1] -- default: ```0.5```)
            The Polygon's inner area alpha value

        muted_alpha:float (values in [0,1] -- default: ```0```)
            The Polygon's overall alpha when disabled from the legend

        **kwargs: Dict
            Other arguments related to the creation of a polygon
        
        Returns
        -------
        renderer: Bokeh polygon instance
            The instance of the added polygon
        """
        if polygon_type not in ALLOWED_BASIC_POLYGON_TYPES:
            raise ValueError(f'polygon_type must be one of the following: {ALLOWED_BASIC_POLYGON_TYPES}')

        coordinates = [f'{col}{self.__suffix}' for col in self.sp_columns]

        renderer = getattr(self.figure, polygon_type)(*coordinates, line_width=line_width, line_color=line_color, fill_color=fill_color, nonselection_fill_color=sec_color, fill_alpha=fill_alpha, muted_alpha=muted_alpha, source=self.source, **kwargs)
        self.renderers.append(renderer)

        return renderer
        
    
    def add_map_tile(self, provider, retina=True, level='underlay', **kwargs):
        """
        Add a Map Tile to the Canvas
            
        Parameters
        ----------
        provider: str
            A map tile provider (available: CARTODBPOSITRON, STAMEN_TERRAIN, STAMEN_TONER, STAMEN_TONER_BACKGROUND, STAMEN_TONER_LABELS)
        retina: boolean (default:True)            
            If True, tiles will be downloaded in Retina Resolution (some providers do not offer retina resolution)        
        level: str (default: ```'underlay'```)
            The z-order of the map tiles. 'underlay' means that the map tiles will be always at the back of the plot (i.e., z-order=0)
        **kwargs: Dict
            Other parameters related to the map tile creation
        """
        if provider == 'CARTODBPOSITRON':
            vendor = Vendors.CARTODBPOSITRON_RETINA if retina else Vendors.CARTODBPOSITRON
        elif provider == 'STAMEN_TERRAIN':
            vendor = Vendors.STAMEN_TERRAIN_RETINA if retina else Vendors.STAMEN_TERRAIN
        elif provider == 'STAMEN_TONER':
            vendor = Vendors.STAMEN_TONER
        elif provider == 'STAMEN_TONER_BACKGROUND':
            vendor = Vendors.STAMEN_TONER_BACKGROUND
        elif provider == 'STAMEN_TONER_LABELS':   
            vendor = Vendors.STAMEN_TONER_LABELS
        
        tile_provider = get_provider(vendor)
        self.figure.add_tile(tile_provider, level=level, **kwargs)

    
    def add_hover_tooltips(self, tooltips, **kwargs):
        """
        Add a Hover Tool to the Canvas.
            
        Parameters
        ----------
        tooltips: List
            A list of tuples containing the label and the respective column name prefixed by ```@``` (e.g. [..., ('o_id', '@o_id_column'), ....])
        **kwargs: Dict
            Other parameters related to the Hover Tool creation
        """
        # Add the HoverTool to the figure
        self.figure.add_tools(HoverTool(tooltips=tooltips, **kwargs))


    def add_lasso_select(self, **kwargs):
        """
        Add a Lasso Select Widget to the Canvas
            
        Parameters
        ----------
        **kwargs: Other parameters related to the Lasso Select Tool creation
        """
        # Add the HoverTool to the figure
        self.figure.add_tools(bokeh_mdl.LassoSelectTool(**kwargs))


    def add_temporal_filter(self, temporal_name='ts', temporal_unit='s', step_ms=3600000, title='Temporal Horizon', height_policy='min', callback_policy='value_throttled', callback_class=None, **kwargs):
        """
        Add a Temporal Filter to the Canvas
        
        Parameters
        ----------
        temporal_name: str (default: ```'ts'```)
            The column name of the loaded dataset that contains the temporal information
        temporal_unit: str (default: ```'s'```)
            The unit (e.g., seconds -- s) of the temporal information
        step_ms: float (default: 3600000 -- 1 hr.)
            The step (in ms) of the temporal filter
        title: str (default: 'Temporal Horizon')
            The title of the temporal filter
        height_policy: str (default: 'min')
            Describes how the component should maintain its height (accepted values: 'auto', 'fixed', 'fit', 'min', 'max')
            From: https://docs.bokeh.org/en/1.1.0/docs/reference/models/layouts.html#bokeh.models.layouts.LayoutDOM.height_policy
        callback_policy: str (default: 'value_throttled')
            Describes when the callback will be triggered. If callback_policy == 'value', the callback will be fired with each change, 
            while if callback_policy == 'value_throttled' the callback will be executed only when the value is set (i.e., on mouseup).
        callback_class: callbacks.BokehFilters (default: None)
            Allows custom callback methods to be set. If None, the baseline callback method is used.
        **kwargs: Dict
            Other parameters related to the filter creation
        """
        kwargs.pop('value', None) 

        step = step_ms

        start_date = pd.to_datetime(self.data[temporal_name].min(), unit=temporal_unit)
        end_date   = pd.to_datetime(self.data[temporal_name].max(), unit=temporal_unit)

        temp_filter = bokeh_mdl.DateRangeSlider(start=start_date, end=end_date, value=(start_date, end_date), step=step, title=title, height_policy=height_policy, **kwargs)
        temp_filter.format = '%d %b %Y %H:%M:%S.%3N'


        if callback_class is None:
            class Callback(callbacks.BokehFilters):
                def __init__(self, vsn_instance, widget):
                    super().__init__(vsn_instance, widget)
                
                def callback(self, attr, old, new):
                    self.callback_filter_data()

                    new_horizon = self.widget.value
                    new_start = pd.to_datetime(new_horizon[0], unit='ms')
                    new_end   = pd.to_datetime(new_horizon[1], unit='ms')

                    # self.widget.title = (f'{title}: {new_start}...{new_end}')

                    new_pts = self.get_data()
                    new_pts = new_pts.loc[pd.to_datetime(new_pts[temporal_name], unit=temporal_unit).between(new_start, new_end)]

                    self.callback_prepare_data(new_pts, self.widget.id==self.vsn_instance.aquire_canvas_data)
            callback_class = Callback
        
        temp_filter.on_change(callback_policy, callback_class(self, temp_filter).callback)
        self.widgets.append(temp_filter)

    
    def add_categorical_filter(self, title='Category', categorical_name='City_Country', height_policy='min', callback_class=None, **kwargs):
        """
        Add a Categorical Filter to the Canvas
        
        Parameters
        ----------
        title: str (default: 'Category')
            The title of the categorical filter
        categorical_name: str (default: ```'City_Country'```)
            The column name of the loaded dataset that contains the categorical information
        height_policy: str (default: 'min')
            Describes how the component should maintain its height (accepted values: 'auto', 'fixed', 'fit', 'min', 'max')
            From: https://docs.bokeh.org/en/1.1.0/docs/reference/models/layouts.html#bokeh.models.layouts.LayoutDOM.height_policy
        callback_class: callbacks.BokehFilters (default: None)
            Allows custom callback methods to be set. If None, the baseline callback method is used.
        **kwargs: Dict
            Other parameters related to the filter creation
        """
        kwargs.pop('value', None)
        kwargs.pop('options', None)

        options = [('', 'Select...')]
        options.extend([(i, i) for i in sorted(self.data[categorical_name].unique())])

        cat_filter = bokeh_mdl.Select(title=title, options=options, value=options[0][0], height_policy=height_policy, **kwargs)

        if callback_class is None:
            class Callback(callbacks.BokehFilters):
                def __init__(self, vsn_instance, widget):
                    super().__init__(vsn_instance, widget)
                
                def callback(self, attr, old, new):
                    self.callback_filter_data()

                    cat_value = self.widget.value
                    new_pts = self.get_data()

                    # print (cat_value, categorical_name)
                    if cat_value:
                        new_pts = new_pts.loc[new_pts[categorical_name] == cat_value].copy()
                    
                    self.callback_prepare_data(new_pts, self.widget.id==self.vsn_instance.aquire_canvas_data)
            
            callback_class = Callback

        cat_filter.on_change('value', callback_class(self, cat_filter).callback)
        self.widgets.append(cat_filter)
    

    def add_numerical_filter(self, filter_mode='>=', title='Value', numeric_name='Altitude', step=50, height_policy='min', callback_policy='value_throttled', callback_class=None, **kwargs):
        """
        Add a Numerical Filter to the Canvas

        Parameters
        ----------
        filter_mode: str (default: >=)
            The operator that the filter will use on the loaded dataset (allowed operators: '<', '<=', '>', '>=', '==', '!=', 'range')

        title: str (default: 'Value')
            The title of the categorical filter
        numeric_name: str (default: ```'Altitude'```)
            The column name of the loaded dataset that contains the numeric information
        step: float (default: 50)
            The step in which the filter will move within the numeric range of the dataset.
        height_policy: str (default: 'min')
            Describes how the component should maintain its height (accepted values: 'auto', 'fixed', 'fit', 'min', 'max')
            From: https://docs.bokeh.org/en/1.1.0/docs/reference/models/layouts.html#bokeh.models.layouts.LayoutDOM.height_policy
        callback_policy: str (default: 'value_throttled')
            Describes when the callback will be triggered. If callback_policy == 'value', the callback will be fired with each change, 
            while if callback_policy == 'value_throttled' the callback will be executed only when the value is set (i.e., on mouseup).
        callback_class: callbacks.BokehFilters (default: None)
            Allows custom callback methods to be set. If None, the baseline callback method is used.
        **kwargs: Dict
            Other parameters related to the filter creation
        """
        kwargs.pop('value', None)
        
        if filter_mode not in list(ALLOWED_FILTER_OPERATORS.keys()):
            raise ValueError(f'filter_mode must be one of the following: {list(ALLOWED_FILTER_OPERATORS.keys())}')
        
        start, end = self.data[numeric_name].agg([np.min, np.max])
        
        if filter_mode != 'range':
            # value = start if value is None else value
            value = start
            num_filter = bokeh_mdl.Slider(start=start, end=end, step=step, value=value, title=title, height_policy=height_policy, **kwargs)
        else:
            # value = (start, end) if value is None else value
            value = (start, end)
            num_filter = bokeh_mdl.RangeSlider(start=start, end=end, step=step, value=value, title=title, height_policy=height_policy, **kwargs)

        if callback_class is None:
            class Callback(callbacks.BokehFilters):
                def __init__(self, vsn_instance, widget):
                    super().__init__(vsn_instance, widget)
                
                def callback(self, attr, old, new):
                    self.callback_filter_data()

                    num_value = new
                    new_pts = self.get_data()

                    if filter_mode == 'range':
                        new_pts = new_pts.loc[new_pts[numeric_name].between(num_value[0], num_value[1], inclusive=True)]
                    else:
                        new_pts = new_pts.loc[ALLOWED_FILTER_OPERATORS[filter_mode](new_pts[numeric_name], num_value)]
            
                    self.callback_prepare_data(new_pts, self.widget.id==self.vsn_instance.aquire_canvas_data)
            
            callback_class = Callback

        num_filter.on_change(callback_policy, callback_class(self, num_filter).callback)
        self.widgets.append(num_filter)
    

    def show_figures(self, figures=None, sizing_mode=None, toolbar_location='above', ncols=None, plot_width=None, plot_height=None, toolbar_options=None, merge_tools=True, notebook=True, doc=None, notebook_url='http://localhost:8888', **kwargs):
        """
        Method Description
            
        Parameters
        ----------
        figures: List (default: None)
            An array of Canvases to display in a grid, given as a list of lists of bokeh.plotting.figure objects. 
            If None, the instance's Canvas, along with its created widgets will be selected.
        sizing_mode: str (default: None)
            How the component should size itself. (allowed values: 'fixed', 'stretch_width', 'stretch_height', 'stretch_both', 'scale_width', 'scale_height', 'scale_both')
        toolbar_location: str (default: 'above')
            Where will the Bokeh Toolbar be located w.r.t. the Canvas (allowed values: 'above', 'below', 'left', 'right')
        ncols: int (default: None)
            Specify the number of columns you would like in your grid. You must only pass an un-nested list of plots (as opposed to a list of lists of plots) when using ncols.        
        plot_width: int (default: None)
            The width you would like all your plots to be. If None the dimensions are automatically calculated.
        plot_height: int (default: None)
            The height you would like all your plots to be. If None the dimensions are automatically calculated.
        toolbar_options: Dict (default: None)
            A dictionary of options that will be used to construct the grid’s toolbar (an instance of ToolbarBox). If none is supplied, ToolbarBox’s defaults will be used.
        merge_tools: boolean (default: True)
            Combine tools from all child plots into a single toolbar.        
        notebook: boolean (default: True)
            Output either at a Jupyter Notebook (True) or at a Browser via Python Script/Local Bokeh Server (False)
        doc: ```bokeh.io.curdoc``` instance (default: None)
            The basic foundation Bokeh uses to render the canvas (along with its widgets).
        notebook_url: str (default: 'http://localhost:8888')
            The IP address of the Jupyter Notebook. 
        **kwargs: Dict
            Other parameters related to the Canvas' output (in case the output is a Jupyter Notebook)
        """
        grid = None

        try:
            if figures is None:
                if len(self.widgets) != 0:
                    figures = [[column(*self.widgets)],[self.figure]]
                else:
                    figures = [[self.figure]]

            grid = bokeh.layouts.gridplot(figures, sizing_mode=sizing_mode, toolbar_location=toolbar_location, ncols=ncols, plot_width=plot_width, plot_height=plot_height, toolbar_options=toolbar_options, merge_tools=merge_tools)
        except TypeError as e:
            print (f'{e}. You must either: \n \t* Pass \'figures\' as a nested list of figures and leave ncols = None; or\n \t* Pass \'figures\' as a list and a non-None value to \'ncols\'.')
            
        def bokeh_app(doc):
            doc.add_root(grid)

        if notebook: 
            reset_output()
            output_notebook(**kwargs)
            show(bokeh_app, notebook_url=notebook_url)
        else:
            bokeh_app(bokeh_io.curdoc() if doc is None else doc)