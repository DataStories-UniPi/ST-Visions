'''
	st_visualizer.py - v2020.05.12

	Authors: Andreas Tritsarolis, Christos Doulkeridis, Yannis Theodoridis and Nikos Pelekis
'''


import sys, os
import operator
import numpy as np
import pandas as pd
import geopandas as gpd
from loguru import logger
import itertools
from itertools import islice
import pyarrow as pa 
import threading, time

import bokeh
import bokeh.io as bokeh_io
import bokeh.plotting as bokeh_plt
import bokeh.models as bokeh_mdl
import bokeh.palettes as palettes

from bokeh.plotting import figure, reset_output, output_notebook, show
from bokeh.models import ColumnDataSource, GeoJSONDataSource, CDSView, HoverTool, WheelZoomTool, GroupFilter, BooleanFilter, CustomJS, Slider, DateSlider
from bokeh.layouts import column, row

# Importing Helper Libraries
from . import geom_helper
from . import filter_callbacks
from . import providers


# Defining Allowed Values (per use-case)
ALLOWED_BASIC_MARKERS = ["asterisk", "circle", "circle_cross", "circle_x", "cross", "dash", 'diamond', 'diamond_cross', 'hex', "inverted_triangle", 'square', 'square_cross', 'square_x', 'triangle']
ALLOWED_BASIC_POLYGON_TYPES = ['multi_polygons', 'patches']
ALLOWED_BASIC_LINE_TYPES = ['hline_stack', 'line', 'multi_line', 'step', 'vline_stack']
ALLOWED_FILTER_OPERATORS = {'==': operator.eq, '!=': operator.ne, '<': operator.lt, '<=': operator.le, '>': operator.gt, '>=': operator.ge, 'range': None}
ALLOWED_CATEGORICAL_COLOR_PALLETES = ['Accent', 'Blues', 'BrBG', 'BuGn', 'Category10', 'Category20', 'Category20b', 'Category20c', 'Cividis', 'Colorblind', 'Dark2', 'GnBu', 'Greens', 'Greys', 'Inferno', 'Magma','OrRd', 'Oranges', 'PRGn', 'Paired', 'Pastel1', 'Pastel2', 'PiYG', 'Plasma', 'PuBu', 'PuBuGn', 'PuOr', 'PuRd', 'Purples', 'RdBu', 'RdGy', 'RdPu', 'RdYlBu', 'RdYlGn', 'Reds', 'Set1', 'Set2', 'Set3', 'Spectral', 'Turbo', 'Viridis', 'YlGn', 'YlGnBu', 'YlOrBr', 'YlOrRd']
ALLOWED_NUMERICAL_COLOR_PALETTES = ['Blues256', 'Greens256', 'Greys256', 'Inferno256', 'Magma256', 'Plasma256', 'Viridis256', 'Cividis256', 'Turbo256', 'Oranges256', 'Purples256', 'Reds256']



class st_visualizer:


    def __init__(self, limit=30000, allow_complex_geometries=False, target_crs=3857, sp_columns=['lon', 'lat'], expected_schema: pa.schema= None ):
        """
        Constructor for creating a VISIONS Instance.
            
        Parameters
        ----------
        limit: int (default: ``30000``)
            The maximum number of geometries (glyphs/polygons/lines) to be visualized.
        allow_complex_geometries: boolean (default: ``False``)
            Choose to plot either the polygons' exterior (False) or along with its inner voids (True)
        target_crs: int (default: ```3857```)
            The target crs that the input geometries will be projected to prior to visualization.
        sp_columns : list of str (Default: ``['lon', 'lat']``). (longitude column, Latitude Column)
            Column names containing spatial coordinates when geometry column is absent.
        expected_schema : pyarrow.Schema, optional (Default: ``None``)
            Expected Arrow schema for CDS Initialization for streaming scenarios. If provided, validates 
            incoming streaming data against schema for type consistency.
        """
        self.limit = limit
        self.allow_complex_geometries = allow_complex_geometries
        self.target_crs = target_crs
        self.sp_columns = sp_columns
        self.expected_schema = expected_schema

        self.data = None
        self.canvas_data = None
        self.figure = None
        self.source = None
        self._bokeh_handle = None

        self.renderers = []
        self.widgets   = []
        self.cmap = None
        self.__suffix = None
        self.aquire_canvas_data = None 
        self._stream = None
        self.is_centered_on_data = False
        self.padding = None
        self.palette = None
        self.filter_col_map = {}

        logger.info(f"VISIONS instance initialized with limit={limit}, target_crs={target_crs}")
        # self._arrow_cache = None

    

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
        data = data.to_crs(self.target_crs)

        self.data = data
        self.sp_columns = columns

    def set_data(self, data, source_crs=4326):
        """
        Loading a Dataset to a VISIONS instance.
            
        Parameters
        ----------
        data: Pandas DataFrame or GeoPandas GeoDataFrame
            The Dataset that will be loaded to the instance
        source_crs: int (default: ```4326```) 
            The CRS of the Dataset's spatial coordinates
        """
        if isinstance(data, dict):
            try:
                table = pa.table(data)
                # data = table.to_pandas()
                try:
                    current_data = pa.Table.from_pandas(
                    self.data.drop(columns=[self.data.geometry.name]),
                    preserve_index=False
                    )

                    combined_table = pa.concat_tables([table, current_data], promote_options='default')
                    if combined_table.num_rows > self.limit:
                        start = combined_table.num_rows - self.limit
                        combined_table = combined_table.slice(start)

                    data = combined_table.to_pandas()
                except Exception as e:
                    logger.warning(f"Arrow concatenation failed, replacing data: {e}")
                    data = table.to_pandas()
            except Exception as e:
                logger.error(f'Cant convert the streaming data to a dataframe')
                raise ValueError(f"Failed to convert streaming data to DataFrame: {e}")

        if not isinstance(data, (gpd.GeoDataFrame, pd.DataFrame)):
            logger.error(f'"data" must be either a Pandas DataFrame or a GeoPandas GeoDataFrame, but got type: { type(data).__name__}')
            raise ValueError('"data" must be either a Pandas DataFrame or a GeoPandas GeoDataFrame')
            

        if not isinstance(data, gpd.GeoDataFrame):
            data = geom_helper.create_geometry(data, coordinate_columns=self.sp_columns, source_crs=source_crs)
        
        self.__set_data(data, self.sp_columns)            


    def set_figure(self, figure=None):
        """
        Load a Canvas to the class' attributes
            
        Parameters
        ----------
        figure: bokeh.plotting.figure instance (default: ``None``)
            The canvas in which the data will be drawn to.
        """
        self.figure = figure

    
    def set_source(self, source=None):
        """
        Load a CDS to the class' attributes
            
        Parameters
        ----------
        figure: bokeh.models.ColumnDataSource instance (default: ``None``)
            The communication 'bridge' that will send data from the loaded dataset to the Canvas.
        """
        self.source = source

    def get_data_stream(self, stream, source_crs=4326, refresh_rate=1000, notebook=False):
        """
        Consume and visualize real-time spatio-temporal data from streaming sources.
        
        Establishes a continuous data pipeline that fetches, processes, and visualizes
        streaming data with automatic updates. Supports both Jupyter notebook and
        Bokeh server deployment modes.

        Uses an Arrow table cache for efficient append operations.

        Parameters
        ----------
        stream : ST_AbstractStream subclass
            Streaming source instance (Kafka, etc.)
        source_crs : int (default: ``4326``).
            Coordinate reference system of the incoming data.
        refresh_rate : int (default: ``1000 ms = 1 second``)
            Update frequency in milliseconds 
        notebook : bool, optional (Default: ``False``)
            * If True, runs in Jupyter notebook mode with thread-based updates.
            * If False, runs in Bokeh server mode with document callbacks.
        """

        if not stream:
            raise ValueError("No stream provided")

        # Initialize Arrow cache if not present
        if not hasattr(self, "_arrow_cache"):
            self._arrow_cache = None

        if not hasattr(self, "_stop_callback"):
            self._stop_callback = threading.Event()
        else:
            # Stop any existing stream before starting a new one
            if not self._stop_callback.is_set():
                logger.info("Existing stream detected, stopping previous one...")
                self.stop_callback()
                time.sleep(0.5)
            self._stop_callback = threading.Event()

        def fetch_data():
            """
            Fetch latest data batch as a PyArrow Table.   
        
            Returns
            -------
            pyarrow.Table or None
                Arrow Table containing new data batch, or None if no data available.
            """
            data_dict = stream.fetch_data(max_points=self.limit)
            if not data_dict:
                return None

            try:
                batch_table = pa.table(data_dict)
                return batch_table
            except Exception as e:
                logger.warning(f"Failed to convert stream data to Arrow Table: {e}")
                return None

        def append_to_cache(batch_table):
            """
            Append new batch to Arrow cache with rollover management.
            
            Parameters
            ----------
            batch_table : pyarrow.Table
                New data batch to append.
            
            Returns
            -------
            pyarrow.Table
                Updated cache after append operation.
            
            Notes
            -----
            Implements FIFO rollover: when cache exceeds `self.limit`, oldest
            records are removed to maintain size constraint.
            """
            try:
                if self._arrow_cache is not None:
                    combined = pa.concat_tables([self._arrow_cache, batch_table], promote_options='default')
                else:
                    combined = batch_table

                if combined.num_rows > self.limit:
                    start = combined.num_rows - self.limit
                    combined = combined.slice(start)

                self._arrow_cache = combined
                return combined

            except Exception as e:
                logger.warning(f"Arrow append failed, resetting cache: {e}")
                self._arrow_cache = batch_table
                return batch_table

        def process_batch(df):
            """
            Convert batch DataFrame to GeoDataFrame with proper geometry and projection.
            
            Parameters
            ----------
            df : pandas.DataFrame
                Raw data batch from stream.
            
            Returns
            -------
            geopandas.GeoDataFrame
                Processed spatial data with projected coordinates and suffix-appended
                lon/lat columns for visualization.
            """
            gdf = geom_helper.create_geometry(df, coordinate_columns=self.sp_columns, source_crs=source_crs)
            gdf = gdf.to_crs(self.target_crs)
    
            gdf[f"lon{self.__suffix}"] = gdf.geometry.x
            gdf[f"lat{self.__suffix}"] = gdf.geometry.y
            return gdf

        
        def st_stream_callback():
            """
            Core streaming callback function executed on each refresh cycle.
            
            """

            batch_table = fetch_data()
            if batch_table is None:
                return
            
            combined_table = append_to_cache(batch_table)
            batch_df = batch_table.to_pandas()
            data_df = combined_table.to_pandas()
            processed_batch = process_batch(batch_df)
            updated_data = process_batch(data_df)

            self.__set_data(updated_data, self.sp_columns)
            self.prepare_data()

            self.update_filters()
            self.update_colormaps()


            filtered_batch = self.apply_active_filters(processed_batch)

            stream_dict = filtered_batch.drop(columns=[processed_batch.geometry.name]).to_dict(orient="list")

            if self.source is not None:
                valid_cols = set(self.source.data.keys())
                stream_dict = {k: v for k, v in stream_dict.items() if k in valid_cols}
                self.source.stream(stream_dict, rollover=self.limit)
                # logger.info("Streamed batch")
            else:
                logger.warning("No ColumnDataSource available yet — skipping stream.")

            if not self.is_centered_on_data and len(processed_batch) > 0:
                bbox = self.data.total_bounds
                x_min, y_min, x_max, y_max = bbox

                #x_min, x_max = processed_batch[f'lon{self.__suffix}'].min(), processed_batch[f'lon{self.__suffix}'].max()
                #y_min, y_max = processed_batch[f'lat{self.__suffix}'].min(), processed_batch[f'lat{self.__suffix}'].max()

                x_span = x_max - x_min
                y_span = y_max - y_min

                if y_span == 0 or x_span == 0:
                    self.is_centered_on_data = False
                    return

                # get aspect ratio of plot
                fig_aspect = self.figure.width / self.figure.height
                data_aspect_ratio = x_span / y_span

                # Expand y_range or x_range depending on aspect ratio
                if data_aspect_ratio > fig_aspect:
                    new_y_span = x_span / fig_aspect
                    padding = (new_y_span - y_span) / 2
                    y_min -= padding
                    y_max += padding
                else:
                    new_x_span = y_span * fig_aspect
                    padding = (new_x_span - x_span) / 2
                    x_min -= padding
                    x_max += padding



                self.figure.x_range.start = x_min 
                self.figure.x_range.end = x_max 
                self.figure.y_range.start = y_min 
                self.figure.y_range.end = y_max 

                self.is_centered_on_data = True
                # logger.info(f"dynamically bounded to first batch data: X({x_min},{x_max}) Y({y_min},{y_max})")
            
            if notebook:
                try:
                    # Only push if the handle exists
                    if hasattr(self, "_bokeh_handle") and self._bokeh_handle is not None:
                        bokeh_io.push_notebook(handle=self._bokeh_handle)
                    # else:
                       # logger.info("No notebook handle yet, skipping push")
                except Exception as e:
                    logger.warning(f"Notebook update failed: {e}")

            
        if notebook:
            def notebook_periodic_callback():
                """
                Thread-based periodic callback for Jupyter notebook deployment.

                Runs in a separate daemon thread to avoid blocking the notebook
                while maintaining the refresh rate.
                """
                while not self._stop_callback.is_set():
                    try:
                        st_stream_callback()
                        time.sleep(refresh_rate / 1000)
                    except Exception as e:
                        logger.error(f"Notebook streaming error: {e}")
                        break
                logger.info("Notebook thread stopped")

            thread = threading.Thread(target=notebook_periodic_callback, daemon=True)
            thread.start()
            self._notebook_thread = thread
            logger.info("Notebook thread started")
        else:
            # Server mode: Register callback with Bokeh document
            doc = bokeh_io.curdoc()
            doc.add_periodic_callback(st_stream_callback, refresh_rate)
            logger.info("Bokeh periodic callback registered")

    def get_data_csv(self, filepath, source_crs=4326, **kwargs):
        """
        Parse a CSV file as a GeoDataFrame.
            
        Parameters
        ----------
        filepath: str
            The path to the CSV source file
        source_crs: int (default: ```4326```)  
            The CRS of the Dataset's spatial coordinates
        **kwargs: Dict
            Other arguments related to parsing a CSV file (consult pandas.read_csv method)
        """
        data = pd.read_csv(filepath, **kwargs)
        data = geom_helper.create_geometry(data, coordinate_columns=self.sp_columns, source_crs=source_crs)
       
        self.__set_data(data, self.sp_columns)


    def get_data_postgres(self, sql, con, postgis=True, source_crs=4326, **kwargs):
        """
        Parse a PostGIS SQL Result as a GeoDataFrame.
            
        Parameters
        ----------
        sql: str
            The SQL query for fetching the spatial data.
        source_crs: int (default: ```4326```)  
            The CRS of the Dataset's spatial coordinates
        **kwargs: Dict
            Other arguments related to parsing the SQL Result (consult geopandas.read_postgis method)
        """
        if postgis:
            data = gpd.read_postgis(sql, con, source_crs=source_crs, **kwargs)
        else:
            data = pd.read_sql_query(sql, con, **kwargs)
            data = geom_helper.create_geometry(data, coordinate_columns=self.sp_columns, source_crs=source_crs)

        self.__set_data(data, self.sp_columns)


    def prepare_data(self, data=None, suffix=None):
        """
        Prepare the (loaded) data prior to rendering. 

        Parameters
        ----------
        data: GeoPandas GeoDataFrame (default: ``None``)
            Prepare either the loaded data (None) or another DataFrame
        suffix: str (default: ``None``)
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
            logger.error('You must either set a Dataset and/or set a Column suffix for extracted geometry coordinates.')
            raise ValueError('Invalid Parameters for Geometry')
        
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
            logger.error('You must set a DataFrame first')
            raise ValueError('No DataFrame set')

        # data_merc = self.data.iloc[:self.limit if limit is None else limit].copy()
        data_merc = self.prepare_data(suffix=suffix)

        source = ColumnDataSource(data_merc.drop([data_merc.geometry.name], axis=1))        
        # print (source.to_df())

        self.set_source(source)
        self.__suffix = suffix

    def create_canvas(self, title, x_range=None, y_range=None, tile_provider='CARTODBPOSITRON', suffix='_merc', padding=0.30, tile_kwargs={}, **kwargs):        
        """
        Create the instance's Canvas and CDS. Handles both static datasets and real-time streaming scenarios.

        In the case of real-time streaming, the method uses the expected schema as a baseline to initialize an empty CDS that's ready to receive data from a stream

        Parameters
        ----------
        title: str
            The Canvas' title. If the limit set at the constructor is less than the length of the loaded data, the title will be suffixed by ``` - Showing {self.limit} out of {len(self.data)} records'```
        x_range: NumPy Array
            The Canvas' spatial horizon at the longitude dimension
        y_range: Numpy Array
            The Canvas' spatial horizon at the latitude dimension
        tile_provider : str or WMTSTileSource
            Either a provider name string (e.g., 'osm') from the allowed or
            an existing WMTSTileSource instance.
        suffix: str (default: ```'_merc'```)
            A suffix for the column name of the extracted spatial coordinates
        padding : float, optional (Default: ``0.30`` = 30% Padding)
            Padding factor added to data bounds when calculating automatic ranges.
        tile_kwargs: Dict (Default: ``Empty Dict``)
            Additional Keyword arguments related to the tile provider of the instance's canvas (consult the WMTSTileSource Docs)
            https://docs.bokeh.org/en/latest/docs/reference/models/tiles.html
        **kwargs: Dict
            Other arguments related to creating the instance's Canvas (consult bokeh.plotting.figure method)
        """
        if self.data is not None:
            if self.limit < len(self.data):
                title = f'{title} - Showing {self.limit} out of {len(self.data)} records'
            bbox = self.data.total_bounds
            x_min, y_min, x_max, y_max = bbox

            x_span = x_max - x_min
            y_span = y_max - y_min

            
            pad_x = x_span * padding
            pad_y = y_span * padding

            x_min -= pad_x
            x_max += pad_x
            y_min -= pad_y
            y_max += pad_y

            
            if x_range is None:
                x_range = (x_min, x_max)
            if y_range is None:
                y_range = (y_min, y_max)
            
            self.padding = padding

        elif self.source is not None and len(self.source.data) > 0:
            try:
                x = np.array(self.source.data.get(f'lon{suffix}', []))
                y = np.array(self.source.data.get(f'lat{suffix}', []))
                if len(x) > 0 and len(y) > 0:
                    x_range = (np.nanmin(x), np.nanmax(x))
                    y_range = (np.nanmin(y), np.nanmax(y))
            except Exception as e:
                logger.warning(f"Could not infer bounds from source: {e}")

        #Default to empty full map if nothing to show
        if x_range is None or y_range is None:
            x_range = (-2.003e7, 2.003e7)
            y_range = (-2.003e7, 2.003e7)
            logger.info("No data found — created empty canvas")
        
        fig = figure(x_range=x_range, y_range=y_range, x_axis_type="mercator", y_axis_type="mercator", title=title, match_aspect=True, aspect_ratio=4/3, **kwargs)
        self.set_figure(fig)

        try:
            providers.add_tile_to_canvas(self, tile_provider=tile_provider, **tile_kwargs)
            # logger.info(f"Tile provider '{tile_provider}' added successfully.")
        except Exception as e:
            logger.error(f"Failed to add tile provider: {e}")

        
        if self.source is None:
            title = f'{title} - Showing Data Streaming Records'
            if self.data is not None:
                self.create_source(suffix)
            else:
                if self.expected_schema is not None:
                    cds_columns = []

                    for field in self.expected_schema:
                        col = field.name

                        if col in self.sp_columns:
                            cds_columns.append(f'{col}{suffix}')
                        else:
                            cds_columns.append(col)
                            
                    # cds_columns = [field.name for field in self.expected_schema]
                    logger.info(f"Using expected_schema for CDS: {cds_columns}")
                    
                else:
                    cds_columns = [f"{col}{suffix}" for col in self.sp_columns]
                    logger.info(f"No schema found, using default spatial columns: {cds_columns}")

                empty_dict = {col: [] for col in cds_columns}
                self.source = ColumnDataSource(empty_dict)
                self.__suffix = suffix
                self.padding = padding
                logger.info(f"Initialized empty ColumnDataSource with columns: {list(empty_dict.keys())}")

                
                


    def add_categorical_colormap(self, palette, categorical_name, live=False, **kwargs):
        """
        Create a Categorical Colormap. Auto-repeats colors if the number of
        categories exceeds the palette length.
        
        Parameters
        ----------
        palette: str or Tuple 
            The color palette of the colormap. It can either be one of Bokeh's default palettes
            or a Tuple of colors in hexadecimal format.
        categorical_name: str 
            The column name of the loaded dataset that contains the categorical values.
        **kwargs: Dict
            Other arguments related to creating the instance's CategoricalColorMapper
            More info here: https://docs.bokeh.org/en/latest/docs/reference/models/mappers.html#bokeh.models.CategoricalColorMapper
        
        Returns
        -------
        cmap: Dict
            The Categorical Colormap.
        """
        if not (isinstance(palette, tuple) or palette in ALLOWED_CATEGORICAL_COLOR_PALLETES):
            logger.error(f'❌ Invalid palette: "{palette}". Must be a tuple or one of the allowed palettes: {ALLOWED_CATEGORICAL_COLOR_PALLETES}')
            raise ValueError(f'Invalid Palette Name/Tuple.')
        
        if live:
            logger.info(f"Creating live categorical colormap for '{categorical_name}' (will auto-update)")
            categories = ['Loading...']
        else:
            categories = sorted(np.unique(self.source.data[categorical_name]).tolist())


        #categories = sorted(np.unique(self.source.data[categorical_name]).tolist())
        num_categories = len(categories)

        if isinstance(palette, tuple):
            base_colors = palette
        else:
            available_sizes = getattr(palettes, palette).keys()
            max_size = max(available_sizes)
            base_colors = getattr(palettes, palette)[max_size]
            
        # General umbrella fallback zip method that runs even if the colors are enough.
        full_palette = list(islice(itertools.cycle(base_colors), num_categories))

        # Create the CategoricalColorMapper instance
        cmap = bokeh_mdl.CategoricalColorMapper(palette=full_palette, factors=categories, **kwargs)
        self.cmap = {'field': categorical_name, 'transform': cmap}
        self.palette = palette

        return self.cmap

    
    def add_numerical_colormap(self, palette, numeric_name, live= False, val_range=None, nan_color='gray', colorbar=True, cb_orientation='vertical', cb_location='right', label_standoff=12, border_line_color=None, location=(0,0), **kwargs): 
        """
        Apply quantitative color mapping to numerical data.
        
        Creates a linear color mapping that translates numerical values from a
        specified data column into a continuous color gradient. Supports automatic
        color bar generation with configurable placement and styling.
            
        Parameters
        ----------
        palette: str or Tuple 
            The color palette of the colormap. Cam Be:
                * Predefined palette name from `ALLOWED_NUMERICAL_COLOR_PALETTES`
                * Custom tuple of hex color strings (e.g., ``('#FF0000', '#00FF00', '#0000FF')``)
        numeric_name: str 
            The column name of the loaded dataset that contains the numerical values
        val_range : tuple of float (Default: ``None``)
            Custom value range for color mapping as (min, max).
            If None, automatically uses min/max from the data column.
        nan_color: str or bokeh.colors instance (default: ```'gray'```)
            The color name for the geometries that are outside the range of the colormap
        colorbar: boolean (default: True)
            Draw a colorbar alongside the Canvas
        cb_orientation: str (either ```'vertical'```, ```'horizontal'```)
            The orientation of the colorbar
        cb_location: str (either ```'left'```, ```'right'```, ```'above'```, ```'below'```)
            The location of the colorbar relative to the Canvas
        label_standoff: int (default: ``12``)
            The distance (in pixels) to separate the tick labels from the color bar.
        border_line_color: str or bokeh.colors instance (default: ``None``)
            The color of the border of the colorbar        
        location: Tuple (int, int)
            Adjust the colorbar location relative to ```cb_orientation``` and ```cb_location```
        **kwargs: Dict
            Other arguments related to the creation of the colorbar
            read more: 
                * Bokeh Color Mappers: https://docs.bokeh.org/en/latest/docs/reference/models/mappers.html
                * Bokeh Palettes: https://docs.bokeh.org/en/latest/docs/reference/palettes.html
        
        Returns
        -------
        cmap: Dict
            Color mapping configuration dictionary with keys:
            - 'field': str - The data column name used for coloring
            - 'transform': bokeh.models.LinearColorMapper - The color mapper object
        """
        if not (palette in ALLOWED_NUMERICAL_COLOR_PALETTES or isinstance(palette, palettes.Palette.__origin__)):
            logger.error(f'❌ Invalid palette: "{palette}". Must be a tuple or one of the allowed palettes: {ALLOWED_NUMERICAL_COLOR_PALETTES}')          
            raise ValueError(f'Invalid Palette.')
        
        if live:
            logger.info(f"Creating live numerical colormap for '{numeric_name}' (will auto-update)")
            min_val, max_val = val_range if val_range is not None else (0, 1)  # Default placeholder
    
        # Static mode: use data or provided range
        else:
            if self.data is None or numeric_name not in self.data.columns:
                raise ValueError(f"Cannot create colormap: column '{numeric_name}' not found in data")
        
            min_val, max_val = self.data[numeric_name].agg(['min', 'max']) if val_range is None else val_range


        #min_val, max_val = self.data[numeric_name].agg(['min', 'max']) if val_range is None else val_range
        cmap = bokeh_mdl.LinearColorMapper(
            palette=getattr(palettes, palette) if palette in ALLOWED_NUMERICAL_COLOR_PALETTES else palette, 
            low=min_val, 
            high=max_val, 
            nan_color=nan_color
        )
    
        if colorbar:
            cbar = bokeh_mdl.ColorBar(orientation=cb_orientation, color_mapper=cmap, label_standoff=label_standoff, border_line_color=border_line_color, location=location, **kwargs) # Other Params: height=height, width=width
            self.figure.add_layout(cbar, cb_location)

        # self.cmap = {'type':'add_numerical_colormap', 'cmap':{'field': numeric_name, 'transform': cmap}}
        self.cmap = {'field': numeric_name, 'transform': cmap}
        return self.cmap


    def add_marker(self, marker='circle', size=10, color='royalblue', sec_color='lightslategray', alpha=0.7, muted_alpha=0, **kwargs):
        """
        Add point marker glyphs to visualize spatial data on the canvas.
        
        Creates scatter plot markers for point geometries with configurable appearance
        and interactive behavior. Supports data-driven coloring when used with
        colormap configurations and integrates with the library's interactive
        filtering and legend systems.
            
        Parameters
        ----------
        marker : str (Default: ``Circle``)
            Glyph marker type. Must be one of `ALLOWED_BASIC_MARKERS`.
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
            Additional keyword arguments passed to `bokeh.plotting.figure.scatter()`.
            More info: https://docs.bokeh.org/en/latest/docs/reference/plotting/figure.html#bokeh.plotting.figure.Figure.scatter
        
        Returns
        -------
        renderer: Bokeh scatter instance
            The instance of the added marker glypths
        """
        if marker not in ALLOWED_BASIC_MARKERS:
            logger.error(f'Invalid marker: "{marker}". Allowed markers are: {ALLOWED_BASIC_MARKERS}')
            raise ValueError(f'Invalid Marker')
        
        coordinates = [f'{col}{self.__suffix}' for col in self.sp_columns]

        renderer = self.figure.scatter(
            *coordinates,
            size = size,
            marker = marker,
            color = color,
            nonselection_fill_color=sec_color,
            alpha = alpha,
            muted_alpha = muted_alpha,
            source = self.source,
            **kwargs
            )

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
            logger.error(f'Invalid line_type: "{line_type}". Allowed types are: {ALLOWED_BASIC_LINE_TYPES}')
            raise ValueError(f'Invalid line type.')

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
            logger.error(f'Invalid line_type: "{polygon_type}". Allowed types are: {ALLOWED_BASIC_POLYGON_TYPES}')
            raise ValueError(f'Invalid Line Type')

        coordinates = [f'{col}{self.__suffix}' for col in self.sp_columns]

        renderer = getattr(self.figure, polygon_type)(*coordinates, line_width=line_width, line_color=line_color, fill_color=fill_color, nonselection_fill_color=sec_color, fill_alpha=fill_alpha, muted_alpha=muted_alpha, source=self.source, **kwargs)
        self.renderers.append(renderer)

        return renderer

    
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


    def add_temporal_filter(self, temporal_name='ts', temporal_unit='s', live=False, step_ms=3600000, start_date=None, end_date=None, title='Temporal Horizon', height_policy='min', callback_policy='value_throttled', callback_class=None, **kwargs):
        """
        Add a Temporal Filter to the Canvas

        Creates a DatetimeRangeSlider widget that allows users to filter data
        within a specified time window. Supports both static datasets and live
        streaming data with automatic time range adjustment.
        
        Parameters
        ----------
        temporal_name: str (default: ```'ts'```)
            The column name of the loaded dataset that contains the temporal information
        temporal_unit: str (default: ```'s'```)
            The unit (e.g., seconds -- s) of the temporal information
        live : bool (Default: ``False``)
            Defines filter behavior depending on enviroment
                * **Static mode** (`live=False`): Filter range fixed to data min/max or
                custom `start_date`/`end_date`. Ideal for historical data exploration.
                * **Live mode** (`live=True`): Filter range dynamically adjusts for
                streaming data. Creates placeholder range that updates with incoming data.
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

        # Live streaming mode: Create placeholder range
        if live:
            template_start = pd.to_datetime(0, unit=temporal_unit)
            template_end   = pd.to_datetime(10, unit=temporal_unit)

            temp_filter = bokeh.models.DatetimeRangeSlider(
                title=title,
                start= template_start,
                end=template_end,
                value=(template_start, template_end),
                step=step,
                format='%d %b %Y %H:%M:%S.%3N',
                bar_color="royalblue",
                height_policy=height_policy,
                **kwargs
            )

        # Static mode: Use data-based range
        else:
            start_date = (pd.to_datetime(self.data[temporal_name].min(), 
                        unit=temporal_unit)) if start_date is None else start_date
            
            end_date = (pd.to_datetime(self.data[temporal_name].max(), 
                    unit=temporal_unit)) if end_date is None else end_date

            temp_filter = bokeh.models.DatetimeRangeSlider(
                title=title,
                start=start_date,
                end=end_date,
                value=(start_date, end_date), 
                step=step, 
                format='%d %b %Y %H:%M:%S.%3N',
                bar_color="royalblue", 
                min_width= 500,
                height_policy=height_policy,
                **kwargs
            )
        
        self.filter_col_map[temp_filter] = (temporal_name, None)

        # Set up callback mechanism
        if callback_class is None:
            class Callback(filter_callbacks.ST_BokehFilters):
                def __init__(self, vsn_instance, widget):
                    super().__init__(vsn_instance, widget)
                
                def callback(self, attr, old, new):
                    if self.vsn_instance.data is None or self.vsn_instance.data.empty:
                        return  # skip
                    
                    self.callback_filter_data()
                    full_data = self.get_data()
                    filtered_data = self.vsn_instance.apply_active_filters(full_data)

                    #new_horizon = self.widget.value
                    #new_start = pd.to_datetime(new_horizon[0], unit='ms')
                    #new_end   = pd.to_datetime(new_horizon[1], unit='ms')

                    #logger.info(new_horizon)

                    # self.widget.title = (f'{title}: {new_start}...{new_end}')

                    #new_pts = self.get_data()
                    #new_pts = new_pts.loc[pd.to_datetime(new_pts[temporal_name], unit=temporal_unit).between(new_start, new_end)]

                    #self.callback_prepare_data(new_pts, True)
                    self.callback_prepare_data(filtered_data)
            callback_class = Callback
        
        temp_filter.on_change(callback_policy, callback_class(self, temp_filter).callback)
        self.widgets.append(temp_filter)

        return temp_filter

    
    def add_categorical_filter(self, title='Vessel Type', live=False, categorical_name='vessel_type', height_policy='min', callback_class=None, **kwargs):
        """
        Add a Categorical Filter to the Canvas
        
        Parameters
        ----------
        title: str (default: 'Category')
            The title of the categorical filter
        categorical_name: str (default: ```'vessel_type'```)
            The column name of the loaded dataset that contains the categorical information
        live : bool (Default: ``False``)
            Defines filter behavior depending on enviroment
                * **Static mode** (`live=False`): Filter range fixed to data min/max or
                custom `start_date`/`end_date`. Ideal for historical data exploration.
                * **Live mode** (`live=True`): Filter range dynamically adjusts for
                streaming data. Creates placeholder range that updates with incoming data.
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

        if live:
            options = [('', 'Select...')]
            cat_filter = bokeh_mdl.Select(title=title, options=options, value=options[0][0], height_policy=height_policy, **kwargs)
            
        else:
            options = [('', 'Select...')]
            options.extend([(i, i) for i in sorted(self.data[categorical_name].unique())])

            cat_filter = bokeh_mdl.Select(title=title, options=options, value=options[0][0], height_policy=height_policy, **kwargs)

        self.filter_col_map[cat_filter] = (categorical_name, None)

        if callback_class is None:
            class Callback(filter_callbacks.ST_BokehFilters):
                def __init__(self, vsn_instance, widget):
                    super().__init__(vsn_instance, widget)
                
                def callback(self, attr, old, new):
                    if self.vsn_instance.data is None or self.vsn_instance.data.empty:
                        return  # skip
                    
                    self.callback_filter_data()
                    full_data = self.get_data()
                    filtered_data = self.vsn_instance.apply_active_filters(full_data)

                    #cat_value = self.widget.value
                    #new_pts = self.get_data()

                    # print (cat_value, categorical_name)
                    #if cat_value:
                        #new_pts = new_pts.loc[new_pts[categorical_name] == cat_value].copy()
                    
                    #self.callback_prepare_data(new_pts, self.widget.id==self.vsn_instance.aquire_canvas_data)
                    self.callback_prepare_data(filtered_data)
            
            callback_class = Callback

        cat_filter.on_change('value', callback_class(self, cat_filter).callback)
        self.widgets.append(cat_filter)
        
        return cat_filter
    
    def add_numerical_filter(self, filter_mode='>=', title='Value', numeric_name='speed', live=False, step=50, height_policy='min', callback_policy='value_throttled', callback_class=None,  **kwargs):
        """
        Add a Numerical Filter to the Canvas

        Parameters
        ----------
        filter_mode: str (default: >=)
            The operator that the filter will use on the loaded dataset (allowed operators: '<', '<=', '>', '>=', '==', '!=', 'range')

        title: str (default: 'Value')
            The title of the categorical filter
        numeric_name: str (default: ```'speed'```)
            The column name of the loaded dataset that contains the numeric information
        live : bool (Default: ``False``)
            Defines filter behavior depending on enviroment
                * **Static mode** (`live=False`): Filter range fixed to data min/max or
                custom `start_date`/`end_date`. Ideal for historical data exploration.
                * **Live mode** (`live=True`): Filter range dynamically adjusts for
                streaming data. Creates placeholder range that updates with incoming data.
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
            logger.error(f' filter_mode must be one of the following: {list(ALLOWED_FILTER_OPERATORS.keys())}')
            raise ValueError(f' Invalid Filter Mode.')
        

        if live:

            if filter_mode != 'range':
                num_filter = bokeh_mdl.Slider(start=0, end=1, value=0, step=step, width=800, title=title, height_policy=height_policy, **kwargs)
            else:
                num_filter = bokeh_mdl.RangeSlider(start=0, end=1, value=(0,1) , step=step, width=800, title=title, height_policy=height_policy, **kwargs)
            
        else:
            start, end = self.data[numeric_name].agg(['min', 'max'])

            if filter_mode != 'range':
                # value = start if value is None else value
                value = start
                num_filter = bokeh_mdl.Slider(start=start, end=end, step=step, value=value, width=800, title=title, height_policy=height_policy, **kwargs)
            else:
                # value = (start, end) if value is None else value
                value = (start, end)
                num_filter = bokeh_mdl.RangeSlider(start=start, end=end, step=step, value=value, width=800, title=title, height_policy=height_policy, **kwargs)

        self.filter_col_map[num_filter] = (numeric_name, filter_mode)
        
        if callback_class is None:
            class Callback(filter_callbacks.ST_BokehFilters):
                def __init__(self, vsn_instance, widget):
                    super().__init__(vsn_instance, widget)
                    self.filter_op = ALLOWED_FILTER_OPERATORS[filter_mode]
                    
                
                def callback(self, attr, old, new):
                    if self.vsn_instance.data is None or self.vsn_instance.data.empty:
                        return  # skip
                    
                    self.callback_filter_data()
                    full_data = self.get_data()
                    filtered_data = self.vsn_instance.apply_active_filters(full_data)

                    #num_value = new
                    #new_pts = self.get_data()

                    #if filter_mode == 'range':
                        #new_pts = new_pts.loc[new_pts[numeric_name].between(num_value[0], num_value[1], inclusive='both')]
                    #else:
                        #new_pts = new_pts.loc[self.filter_op(new_pts[numeric_name], num_value)]
            
                    #self.callback_prepare_data(new_pts, self.widget.id==self.vsn_instance.aquire_canvas_data)
                    self.callback_prepare_data(filtered_data)
            
            callback_class = Callback

        num_filter.on_change(callback_policy, callback_class(self, num_filter).callback)
        self.widgets.append(num_filter)

        return num_filter

    

    def update_filters(self):
        """
            Synchronize all active filter widget ranges when receiving new streaming data 
        """

        from contextlib import contextmanager
        @contextmanager
        def suppress_bokeh_callbacks(widget):
            """
            Context manager to temporarily suppress Bokeh widget callbacks.

            Parameters
            ----------
            widget : bokeh.models.Widget
            Widget whose callbacks should be suppressed.

            Yields
            ------
            None
            Enters context with callbacks suppressed.
            """
            old_callbacks = widget._callbacks.copy()
            widget._callbacks.clear()
            yield
            widget._callbacks.update(old_callbacks)

        for widget in self.widgets:
            col_metadata = self.filter_col_map.get(widget)
            if col_metadata is None:
                continue

            column, mode = col_metadata

            if isinstance(widget, bokeh_mdl.Slider) or isinstance(widget, bokeh_mdl.RangeSlider):
                if column is None or self.data is None or self.data.empty:
                    continue
                
                start, end = self.data[column].agg(['min', 'max'])

                with suppress_bokeh_callbacks(widget):
                    widget.start = start
                    widget.end = end
            
            elif isinstance(widget, bokeh_mdl.Select):
                # column = self.filter_col_map.get(widget, None)
                if column is None or self.data is None or self.data.empty:
                    widget.options = [('', 'Select...')]
                    continue

                #cats = sorted(self.data[cname].dropna().unique())
                with suppress_bokeh_callbacks(widget):
                    widget.options = [('', 'Select...')]
                    widget.options.extend([(i, i) for i in sorted(self.data[column].unique())])

            elif isinstance(widget, bokeh_mdl.DatetimeRangeSlider):
                if column is None or self.data.empty:
                    continue

                ts = self.data[column]
                start = ts.min()
                end = ts.max()

                # logger.info((start, end, start < end))

                with suppress_bokeh_callbacks(widget):
                    widget.start = start
                    widget.end = end

    def update_colormaps(self):
        if self.cmap is not None and self.data is not None and not self.data.empty:
            field_name = self.cmap.get('field')
            cmap_transform = self.cmap.get('transform')
            
            if field_name and field_name in self.data.columns:

                if hasattr(cmap_transform, 'low'):  # Numerical colormap
                    new_min = self.data[field_name].min()
                    new_max = self.data[field_name].max()
                    
                    # Only update if range changed
                    if new_min != cmap_transform.low or new_max != cmap_transform.high:
                        cmap_transform.low = new_min
                        cmap_transform.high = new_max
                        #logger.debug(f"Updated numerical colormap range: {field_name} = {new_min:.2f} to {new_max:.2f}")
                
            if hasattr(cmap_transform, 'factors'):  # Categorical
                # Get ALL unique categories from data
                #palette = self.cmap.get('palette')
                all_categories = sorted(self.data[field_name].dropna().unique().tolist())
                old_categories = cmap_transform.factors
                
                merged_categories = list(old_categories)
                
                for cat in all_categories:
                    if cat not in merged_categories:
                        merged_categories.append(cat)  # add new categories
                
                # update if categories changed
                if set(merged_categories) != set(old_categories):
                    cmap_transform.factors = merged_categories
                    #logger.info(f"Updated categorical colormap: {len(merged_categories)} categories")
                    
                    self._update_categorical_palette(cmap_transform, len(merged_categories))

    def _update_categorical_palette(self, color_mapper, num_categories):
        """
        Regenerate palette to match new category count.
        """
        available_sizes = getattr(palettes, self.palette).keys()
        max_size = max(available_sizes)
        base_colors = getattr(palettes, self.palette)[max_size]
        
        full_palette = list(itertools.islice(itertools.cycle(base_colors), num_categories))
        
        color_mapper.palette = full_palette

    
    def apply_active_filters(self, df):
        """
        Apply active filters to a DataFrame

        Parameters
        ----------
        df : pandas.DataFrame 
            Input dataset to filter.

        Returns
        -------
        pandas.DataFrame 
            Filtered data subset.
        """
        result = df

        for widget in self.widgets:
            col_metadata = self.filter_col_map.get(widget)
            if col_metadata is None:
                continue

            column, mode = col_metadata

            if isinstance(widget, bokeh_mdl.Slider):
                #result = result[result[column] >= widget.value]
                result = result[ALLOWED_FILTER_OPERATORS[mode](result[column], widget.value)]

            if isinstance(widget, bokeh_mdl.RangeSlider):
                lo, hi = widget.value
                result = result[result[column].between(lo, hi)]

            if isinstance(widget, bokeh_mdl.Select):
                if widget.value:
                    result = result[result[column] == widget.value]
            
            if isinstance(widget, bokeh_mdl.DatetimeRangeSlider):
                lo, hi = widget.value

                #lo = pd.to_datetime(lo_ms, unit="ms")
                #hi = pd.to_datetime(hi_ms, unit="ms")

                #ts = pd.to_datetime(result[column])
                #logger.info((lo, hi))

                result = result[result[column].between(lo, hi)]
            
        return result
        


    

    def prepare_grid(self, figures=None, sizing_mode=None, toolbar_location='above', ncols=None, width=None, height=None, toolbar_options=None, merge_tools=True):
        """
        Prepare a Bokeh grid layout for figures and widgets.

        Parameters
        ----------
        figures : list or list of lists, optional
            A list of Bokeh figure objects or a nested list of figures to arrange in a grid.
            If None, the grid will be composed of the instance's widgets and figure.
        sizing_mode : str or None, optional
            The sizing mode for the layout (e.g., 'fixed', 'stretch_both', 'scale_width', etc.).
            Passed directly to Bokeh's `gridplot`.
        toolbar_location : str or None, optional, default: 'above'
            Location of the toolbar. Options include 'above', 'below', 'left', 'right', or None.
        ncols : int or None, optional
            Number of columns in the grid. If figures is a nested list, ncols should be None.
            If figures is a flat list, ncols must be specified.
        width : int or None, optional
            Width of each subplot in the grid.
        height : int or None, optional
            Height of each subplot in the grid.
        toolbar_options : dict or None, optional
            Additional options for the toolbar passed to Bokeh's `gridplot`.
        merge_tools : bool, optional, default: True
            Whether to merge tools from all figures into a single toolbar.

        Returns
        -------
        bokeh.layouts.GridBox or None
            A Bokeh grid layout object containing the arranged figures and widgets,
            or None if the grid could not be created due to an error.
    
        """
        grid = None

        try:
            if figures is None:
                if len(self.widgets) != 0:
                    figures = [[column(*self.widgets)],[self.figure]]
                else:
                    figures = [[self.figure]]

            grid = bokeh.layouts.gridplot(figures, sizing_mode=sizing_mode, toolbar_location=toolbar_location, ncols=ncols, width=width, height=height, toolbar_options=toolbar_options, merge_tools=merge_tools)
        except TypeError as e:
            logger.error(f"{e}.\nYou must either:\n\t* Pass 'figures' as a nested list of figures and leave ncols = None;\n\t* Pass 'figures' as a list and a non-None value to 'ncols'.")
            # print (f'{e}. You must either: \n \t* Pass \'figures\' as a nested list of figures and leave ncols = None; or\n \t* Pass \'figures\' as a list and a non-None value to \'ncols\'.')
            
        return grid


    def show_figures(self, live=False, figures=None, sizing_mode=None, toolbar_location='above', ncols=None, width=None, height=None, toolbar_options=None, merge_tools=True, notebook=True, doc=None, notebook_url='http://localhost:8888', **kwargs):
        """
        Render a Bokeh grid layout either in a Jupyter notebook or a Bokeh server.
            
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
        
        grid = self.prepare_grid(figures, sizing_mode=sizing_mode, toolbar_location=toolbar_location, ncols=ncols, width=width, height=height, toolbar_options=toolbar_options, merge_tools=merge_tools)

        def bokeh_app(doc):
            doc.add_root(grid)

        if notebook:
            if live:
                reset_output()
                output_notebook(**kwargs)

                self._bokeh_handle = show(
                    grid,
                    notebook_handle=True,
                    notebook_url=notebook_url
                )
                
                # print("Live notebook handle created, use push_notebook() to stream updates.")
            else:
                reset_output()
                output_notebook(**kwargs)
                show(bokeh_app, notebook_url=notebook_url)
        else:
            bokeh_app(bokeh_io.curdoc() if doc is None else doc)
