'''
	express.py - v2020.05.12

	Authors: Andreas Tritsarolis, Christos Doulkeridis, Yannis Theodoridis and Nikos Pelekis
'''    

import bokeh.models as bokeh_models
from st_visions.streaming.st_vizstream import ST_KafkaStream


def plot_points_on_map(obj, tools=None, tile_provider='CARTODBPOSITRON', marker='circle', size=10, color='royalblue', alpha=0.7, fill_alpha=0.6, muted_alpha=0, legend_label=f'Object GPS Locations', sizing_mode='scale_width', tile_kwargs={}, **kwargs):
    '''
        Visualize a Point Geometry Dataset on the map.

        Parameters
        ----------        
        obj: st_visualizer 
            A VISIONS instance
        tools: List(str)
            A list of Bokeh tools (https://docs.bokeh.org/en/latest/docs/user_guide/tools.html)
        tile_provider: str (default: "CARTODBPOSITRON")
            The name of the map provider (Built-in values: CARTODBPOSITRON, STAMEN_TERRAIN, STAMEN_TONER, OSM). Accepts custom WMTSTileSource instances.
        marker: str (default: "circle")
            The type of the marker that will be used when rendering the data
        size: int (default: 10)
            The Markers' size
        color: str or bokeh.colors instance (default: ```'royalblue'```)
            The Markers' primary color
        alpha: float (values in [0,1] -- default: ```0.7```)
            The Markers' overall alpha
        fill_alpha: float (values in [0,1] -- default: ```0.7```)
            The Markers' inner area alpha
        muted_alpha: float (values in [0,1] -- default: ```0```)
            The Markers' alpha when disabled from the legend
        legend_label: str (default: "Object GPS Locations")
            The label that will represent the point geometries on the legend
        sizing_mode: str (default: scale_width)
            How the component should size itself. (allowed values: 'fixed', 'stretch_width', 'stretch_height', 'stretch_both', 'scale_width', 'scale_height', 'scale_both')
        tile_kwargs: Dict
            Additional Keyword arguments related to the tile provider of the instance's canvas (consult the WMTSTileSource Docs)
            https://docs.bokeh.org/en/latest/docs/reference/models/tiles.html
        **kwargs: dict
            Other parameters related to the Canvas creation
    '''
    basic_tools = "pan,box_zoom,wheel_zoom,save,reset" 
    extra_tools = f'{basic_tools},{",".join(tools)}' if tools is not None else basic_tools
        
    obj.create_canvas(title=f'Express Plot', tile_provider=tile_provider, sizing_mode=sizing_mode, height=800, tools=extra_tools, **tile_kwargs, **kwargs)

    _ = obj.add_marker(marker=marker, size=size, color=color, alpha=alpha, fill_alpha=fill_alpha, muted_alpha=muted_alpha, legend_label=legend_label)
    obj.figure.toolbar.active_scroll = obj.figure.select_one(bokeh_models.WheelZoomTool)



def plot_polygons_on_map(obj, tools=None, tile_provider='CARTODBPOSITRON', polygon_type='patches', fill_color='royalblue', line_color='royalblue', alpha=1, fill_alpha=0.65, muted_alpha=0, legend_label='Polygon Locations', sizing_mode='scale_width', tile_kwargs={}, **kwargs):
    '''
        Visualize a (Multi)Polygon Geometry Dataset on the map.

        Parameters
        ----------        
        obj: st_visualizer 
            A VISIONS instance
        tools: List(str)
            A list of Bokeh tools (https://docs.bokeh.org/en/latest/docs/user_guide/tools.html)
        tile_provider: str (default: ```CARTODBPOSITRON```)
            The name of the map tile provider (allowed values: CARTODBPOSITRON, STAMEN_TERRAIN, STAMEN_TONER, STAMEN_TONER_BACKGROUND, STAMEN_TONER_LABELS)
        polygon_type: str (default: ```patches```)
            The type of polygon that will be used when rendering the data
        fill_color: ```str``` or ```bokeh.colors``` instance
            The fill color for the (Multi)Polygons
        line_color: ```str``` or ```bokeh.colors``` instance
            The line color for the (Multi)Polygons
        alpha: float (values in [0,1] -- default: ```0.7```)
            The Polygons' overall alpha
        fill_alpha: float (values in [0,1] -- default: ```0.7```)
            The Polygons' inner area alpha
        muted_alpha: float (values in [0,1] -- default: ```0```)
            The Polygons' alpha when disabled from the legend
        legend_label: str (default: ```Polygon Locations```)
            The label that will represent the point geometries on the legend
        sizing_mode: str (default: scale_width)
            How the component should size itself. (allowed values: 'fixed', 'stretch_width', 'stretch_height', 'stretch_both', 'scale_width', 'scale_height', 'scale_both')
        tile_kwargs: Dict
            Additional Keyword arguments related to the tile provider of the instance's canvas (consult the WMTSTileSource Docs)
            https://docs.bokeh.org/en/latest/docs/reference/models/tiles.html
        **kwargs: dict
            Other parameters related to the Canvas creation
    '''
    basic_tools = "pan,box_zoom,wheel_zoom,save,reset" 
    extra_tools = f'{basic_tools},{",".join(tools)}' if tools is not None else basic_tools
        
    obj.create_canvas(title=f'Express Plot', tile_provider=tile_provider, sizing_mode=sizing_mode, height=800, tools=extra_tools, **tile_kwargs, **kwargs)

    _ = obj.add_polygon(polygon_type=polygon_type, fill_color=fill_color, line_color=line_color, alpha=alpha, fill_alpha=fill_alpha, muted_alpha=muted_alpha, legend_label=legend_label)
    obj.figure.toolbar.active_scroll = obj.figure.select_one(bokeh_models.WheelZoomTool)



def plot_lines_on_map(obj, tools=None, tile_provider='CARTODBPOSITRON', line_type='multi_line', line_color="royalblue", line_width=5, alpha=0.7, muted_alpha=0, legend_label='Moving Objects\' Trajectories', sizing_mode='scale_width', tile_kwargs={}, **kwargs):
    '''
        Visualize a (Multi)LineString Geometry Dataset on the map.

        Parameters
        ----------        
        obj: st_visualizer 
            A VISIONS instance
        tools: List(str)
            A list of Bokeh tools (https://docs.bokeh.org/en/latest/docs/user_guide/tools.html)
        tile_provider: str (default: ```CARTODBPOSITRON```)
            The name of the map tile provider (allowed values: CARTODBPOSITRON, STAMEN_TERRAIN, STAMEN_TONER, STAMEN_TONER_BACKGROUND, STAMEN_TONER_LABELS)
        line_type: str (default: ```multi_line```
            The type of the line that will be used when rendering the data
        line_color: ```str``` or ```bokeh.colors``` instance
            The lines' primary color (i.e., the color to use to stroke lines with)
        line_width: int
            The line stroke width (in units of pixels)
        alpha: float (values in [0,1] -- default: ```0.7```)
            The lines' overall alpha
        muted_alpha: float (values in [0,1] -- default: ```0```)
            The lines' alpha when disabled from the legend
        legend_label: str (default: ```Moving Objects' Trajectories```)
            The label that will represent the point geometries on the legend
        sizing_mode: str (default: scale_width)
            How the component should size itself. (allowed values: 'fixed', 'stretch_width', 'stretch_height', 'stretch_both', 'scale_width', 'scale_height', 'scale_both')
        tile_kwargs: Dict
            Additional Keyword arguments related to the tile provider of the instance's canvas (consult the WMTSTileSource Docs)
            https://docs.bokeh.org/en/latest/docs/reference/models/tiles.html
        **kwargs: dict
            Other parameters related to the Canvas creation
    '''
    basic_tools = "pan,box_zoom,wheel_zoom,save,reset" 
    extra_tools = f'{basic_tools},{",".join(tools)}' if tools is not None else basic_tools
        
    obj.create_canvas(title=f'Express Plot', tile_provider=tile_provider, sizing_mode=sizing_mode, height=800, tools=extra_tools, **tile_kwargs, **kwargs)

    _ = obj.add_line(line_type=line_type, line_color=line_color, line_width=line_width, alpha=alpha, muted_alpha=muted_alpha, legend_label=legend_label)
    obj.figure.toolbar.active_scroll = obj.figure.select_one(bokeh_models.WheelZoomTool)


def plot_points_on_map(obj, tools=None, tile_provider='CARTODBPOSITRON', marker='circle', size=10, color='royalblue', alpha=0.7, fill_alpha=0.6, muted_alpha=0, legend_label=f'Object GPS Locations', sizing_mode='scale_width', tile_kwargs={}, **kwargs):
    '''
        Visualize a Point Geometry Dataset on the map.

        Parameters
        ----------        
        obj: st_visualizer 
            A VISIONS instance
        tools: List(str)
            A list of Bokeh tools (https://docs.bokeh.org/en/latest/docs/user_guide/tools.html)
        tile_provider: str (default: "CARTODBPOSITRON")
            The name of the map provider (Built-in values: CARTODBPOSITRON, STAMEN_TERRAIN, STAMEN_TONER, OSM). Accepts custom WMTSTileSource instances.
        marker: str (default: "circle")
            The type of the marker that will be used when rendering the data
        size: int (default: 10)
            The Markers' size
        color: str or bokeh.colors instance (default: ```'royalblue'```)
            The Markers' primary color
        alpha: float (values in [0,1] -- default: ```0.7```)
            The Markers' overall alpha
        fill_alpha: float (values in [0,1] -- default: ```0.7```)
            The Markers' inner area alpha
        muted_alpha: float (values in [0,1] -- default: ```0```)
            The Markers' alpha when disabled from the legend
        legend_label: str (default: "Object GPS Locations")
            The label that will represent the point geometries on the legend
        sizing_mode: str (default: scale_width)
            How the component should size itself. (allowed values: 'fixed', 'stretch_width', 'stretch_height', 'stretch_both', 'scale_width', 'scale_height', 'scale_both')
        tile_kwargs: Dict
            Additional Keyword arguments related to the tile provider of the instance's canvas (consult the WMTSTileSource Docs)
            https://docs.bokeh.org/en/latest/docs/reference/models/tiles.html
        **kwargs: dict
            Other parameters related to the Canvas creation
    '''
    basic_tools = "pan,box_zoom,wheel_zoom,save,reset" 
    extra_tools = f'{basic_tools},{",".join(tools)}' if tools is not None else basic_tools
        
    obj.create_canvas(title=f'Express Plot', tile_provider=tile_provider, sizing_mode=sizing_mode, height=800, tools=extra_tools, **tile_kwargs, **kwargs)

    _ = obj.add_marker(marker=marker, size=size, color=color, alpha=alpha, fill_alpha=fill_alpha, muted_alpha=muted_alpha, legend_label=legend_label)
    obj.figure.toolbar.active_scroll = obj.figure.select_one(bokeh_models.WheelZoomTool)



def plot_streaming_data_on_map_kafka(obj, tools=None, notebook=False, refresh_rate=100, topic_name='st-viz-topic', tile_provider='CARTODBPOSITRON', marker='circle', size=10, color='royalblue', alpha=0.7, fill_alpha=0.6, muted_alpha=0, legend_label=f'Object GPS Locations', sizing_mode='scale_width', tile_kwargs={}, **kwargs):
    '''
        Express plot for visualizing a real-time streaming Point Geometry Dataset on the map.
        Parameters
        ----------        
        obj: st_visualizer 
            A VISIONS instance
        tools: List(str), optional
            A list of additional Bokeh tools to include alongside the defaults (pan, box_zoom, wheel_zoom, save, reset).
            See https://docs.bokeh.org/en/latest/docs/user_guide/tools.html
        notebook: bool (default: False)
            Whether the visualization is being rendered in a Jupyter notebook
        refresh_rate: int (default: 100)
            The interval in milliseconds at which the plot polls for new streaming data
        topic_name: str (default: 'st-viz-topic')
            The name of the Kafka topic to consume streaming data from
        tile_provider: str (default: "CARTODBPOSITRON")
            The name of the map provider (Built-in values: CARTODBPOSITRON, STAMEN_TERRAIN, STAMEN_TONER, OSM). 
            Accepts custom WMTSTileSource instances.
        marker: str (default: "circle")
            The type of the marker that will be used when rendering the data
        size: int (default: 10)
            The markers' size
        color: str or bokeh.colors instance (default: 'royalblue')
            The markers' primary color
        alpha: float (values in [0,1] -- default: 0.7)
            The markers' overall alpha
        fill_alpha: float (values in [0,1] -- default: 0.6)
            The markers' inner area alpha
        muted_alpha: float (values in [0,1] -- default: 0)
            The markers' alpha when disabled from the legend
        legend_label: str (default: "Object GPS Locations")
            The label that will represent the point geometries on the legend
        sizing_mode: str (default: 'scale_width')
            How the component should size itself.
            Allowed values: 'fixed', 'stretch_width', 'stretch_height', 'stretch_both', 'scale_width', 'scale_height', 'scale_both'
        tile_kwargs: dict
            Additional keyword arguments for the tile provider (consult the WMTSTileSource docs:
            https://docs.bokeh.org/en/latest/docs/reference/models/tiles.html)
        **kwargs: dict
            Additional keyword arguments passed to create_canvas (e.g. width)
    '''
    basic_tools = "pan,box_zoom,wheel_zoom,save,reset" 
    extra_tools = f'{basic_tools},{",".join(tools)}' if tools is not None else basic_tools
        
    obj.create_canvas(title=f'Express Plot', tile_provider=tile_provider, sizing_mode=sizing_mode, height=800, tools=extra_tools, **tile_kwargs, **kwargs)

    stream = ST_KafkaStream(topic_name=topic_name)
    obj.get_data_stream(stream=stream, notebook=notebook, refresh_rate=refresh_rate)

    _ = obj.add_marker(marker=marker, size=size, color=color, alpha=alpha, fill_alpha=fill_alpha, muted_alpha=muted_alpha, legend_label=legend_label)
    obj.figure.legend.location = "top_left"
    obj.figure.legend.click_policy = "mute"
    obj.figure.toolbar.active_scroll = obj.figure.select_one(bokeh_models.WheelZoomTool)