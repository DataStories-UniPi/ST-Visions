'''
	geom_helper.py - v2020.05.07

	Authors: Andreas Tritsarolis, Christos Doulkeridis, Yannis Theodoridis and Nikos Pelekis
	
	Notes:	
		* The Methods ```getXYCoords```, ```getPolyCoords```, ```getLineCoords```, ```getPointCoords```, ```multiGeomHandler``` and ```getCoords``` were forked from: Advanced plotting with Bokeh, https://automating-gis-processes.github.io/2017/lessons/L5/advanced-bokeh.html, Last visited at: 09/03/2020.
		* The Method ```quadrat_cut_geometry``` was forked from: https://github.com/gboeing/osmnx/blob/f5eb1fc4f18c1816987de7f0db8d35690dc65f41/osmnx/core.py#L589, Last visited at: 12/03/2020.
'''


import shapely
import shapely.geometry
import shapely.ops
import numpy as np
from tqdm import tqdm
import geopandas as gpd
from loguru import logger


def concatPolyCoords(polyCoords):
    """
	Function for concatenating the coordinates of complex geometries into a single unified list. There is a user guide section on Polygons With Holes As well as a nice example in the reference guide.
	
	```multi_polygon``` data is 4-level list:

	  * list of multi-polygons
	  * each multi-polygon is a list of polygons
	  * each polygon is a list with one exterior and zero or more holes
	  * each exterior/hole is a list of coordinates
	
	From: https://stackoverflow.com/a/56462957 
	"""
    return [[[p['exterior'], *p['holes']] for p in mp] for mp in polyCoords]


def getXYCoords(geometry, coord_index):
    """
    Returns either x or y coordinates from  geometry coordinate sequence. Used with LineString and Polygon geometries.
    """
    coords = np.asarray(geometry.coords)
    return coords[:, coord_index]


def getPolyCoords(geometry, coord_index, complex_geom):
    """
    Returns Coordinates of Polygon using the Exterior of the Polygon.
    """
    exterior_coords = getXYCoords(geometry.exterior, coord_index)

    if complex_geom:
        interior_coords = []
        for interior in geometry.interiors:
            interior_coords.append(getXYCoords(interior, coord_index))

        return [{'exterior': exterior_coords, 'holes': interior_coords}]
    else:
        return exterior_coords


def getLineCoords(geometry, coord_index):
    """
    Returns Coordinates of Linestring object.
    """
    return getXYCoords(geometry, coord_index)


def getPointCoords(geometry, coord_index):
    """
    Returns Coordinates of Point object.
    """
    return [geometry.xy[coord_index][0]]


def multiGeomHandler(multi_geometry, coord_index, geom_type, complex_geom=False):
    """Handle multi-geometries and return coordinates formatted for Bokeh.

    Processes MultiPoint, MultiLineString, or MultiPolygon geometries by merging
    all parts into coordinate arrays separated by np.nan values (Bokeh's format
    requirement).

    Parameters
    ----------
    multi_geometry : shapely.MultiGeometry
        Input multi-geometry (MultiPoint, MultiLineString, or MultiPolygon).
    coord_index : int (accepted values: 0/1)
        The index (x:0, y:1) of the coodinate dimensions to extract.
    geom_type : str
        Geometry type name ('MultiPoint', 'MultiLineString', 'MultiPolygon').
    complex_geom : bool, optional (Default: False)
        If True, returns exterior and interior coordinates for polygons.

    Returns
    -------
    numpy.ndarray or list
        - For simple geometries: 1D array with np.nan separators
        - For complex MultiPolygons: List of dicts with 'exterior' and 'holes' keys

    Notes
    -----
    - For MultiPolygon with complex_geom=True, returns a list of coordinate dicts
      suitable for Bokeh's Patches marker.
    - np.nan separators are required by Bokeh for multi-part geometries.
    """
    coord_arrays = []

    for part in multi_geometry:
        if geom_type == "MultiPoint":
            coords = getPointCoords(part, coord_index)
            coord_arrays.extend([*coords, np.nan])
        elif geom_type == "MultiLineString":
            coords = getLineCoords(part, coord_index)
            coord_arrays.extend([*coords, np.nan])
        elif geom_type == "MultiPolygon":
            if complex_geom:
                coord_arrays.append(getPolyCoords(part, coord_index, complex_geom))
            else:
                coords = getPolyCoords(part, coord_index, complex_geom)
                coord_arrays.extend([*coords, np.nan])

    if geom_type == "MultiPolygon" and complex_geom:
        return concatPolyCoords(coord_arrays)
    else:
        return np.array(coord_arrays)



def getCoords(geom, coord_index, complex_geom=False):
    """
	Returns coordinates ('x' or 'y') of a geometry (Point, LineString or Polygon) as a list (if geometry is LineString or Polygon). Can handle also MultiGeometries.

	Parameters
	----------	
	geom: shapely (Multi)Geometry (Point, LineString or Polygon)
		The input Geometry
	coord_index: Numeric (accepted values: 0/1)
		The index (x:0, y:1) of the coodinate dimensions to be extracted from ```geom```
	complex_geom: Boolean (default: False)
		If ```False``` return the (Multi)Polygon's exterior coordinates, otherwise return both the exterior and interior (i.e., voids/holes) coordinates.

	Returns
	-------
		List (in case of Point, Line or Polygon geometries) or Nested List (in case of MultiPoint, MultiLineString or MultiPolygon geometries)
	"""
    # Check the geometry type
    gtype = geom.geom_type
    
	# "Normal" geometries
    if gtype == "Point":
        return getPointCoords(geom, coord_index)[0]
    elif gtype == "LineString":
        return np.array(getLineCoords(geom, coord_index))
    elif gtype == "Polygon":
        poly_coords = getPolyCoords(geom, coord_index, complex_geom)
        if complex_geom:
            return concatPolyCoords([poly_coords])[0]
        else:
            return poly_coords
    
	# Multi geometries
    else:
        return multiGeomHandler(geom, coord_index, gtype, complex_geom)



def create_linestring_from_points(gdf, column_handlers, **kwargs):
    """
    Create LineStrings from Point Geometries.

	Parameters
	----------
	gdf: GeoPandas GeoDataFrame
		Contains information about the Point Geometries
	column_handlers: List 
		The Columns that will Uniquely Identify each LineString (i.e., Primary Key(s))
	**kwargs: Dict
		Other parameters related to tqdm.pandas
	
	Returns
	-------
	GeoPandas GeoDataFrame
    """
    
    tqdm.pandas(**kwargs)
    geom_col = gdf.geometry.name

    linestrings = (
        gdf.groupby(column_handlers, group_keys=False)
        .progress_apply(
            lambda l: shapely.geometry.LineString([p.coords[0] for p in l[geom_col]])
            if len(l) >= 2
            else shapely.geometry.LineString([l[geom_col].iloc[0].coords[0]] * 2)
        )
        .to_frame()
        .reset_index()
    )

    linestrings.rename(columns={0: 'geom'}, inplace=True)
    linestrings = gpd.GeoDataFrame(linestrings, geometry='geom', crs=gdf.crs)
    return linestrings


def create_geometry(df, coordinate_columns=['lon', 'lat'], source_crs=4326):
    """
    Create a GeoDataFrame from a DataFrame in a much more generalized form.
    """
    return gpd.GeoDataFrame(
        df,
        geometry = gpd.points_from_xy(
            *[
                df[col] for col in coordinate_columns
            ]
        ),
        crs=source_crs
    )


def classify_area_proximity(trajectories, spatial_areas, compensate=False, buffer_amount=1e-14, verbose=True):
    """
    Classify Point Geometries according to their Spatial Proximity to one (or many) Spatial Area(s).

    Parameters
    ----------
    trajectories: GeoPandas GeoDataFrame
        Contains information about the Point Geometries.
    spatial_areas: GeoPandas GeoDataFrame
        Contains information about the Spatial Areas (Polygons).
    compensate: bool, default False
        Buffer each spatial area by `buffer_amount`.
    buffer_amount: float, default 1e-14
        Buffer amount for `spatial_areas` (if `compensate=True`).
    verbose: bool, default True
        Enable or disable verbosity.

    Returns
    -------
    GeoPandas GeoDataFrame
        Updated `trajectories` with an added `area_id` column.
    """
    trajectories = trajectories.copy()
    trajectories['area_id'] = None

    if verbose:
        logger.info(f'Creating spatial index for points...')
    
    # Create spatial index on the points
    sindex = trajectories.sindex
    if verbose:
        logger.info(f"Classifying spatial proximity...")

    for area_id, polygon in tqdm(spatial_areas.geometry.items(), disable=not verbose):
        if compensate:
            polygon = polygon.buffer(buffer_amount).buffer(0)
        possible_matches = sindex.query(polygon, predicate='intersects')
        
        if possible_matches.size == 0:
            continue  

        # Filter precise matches
        matched = trajectories.loc[possible_matches]
        intersects = matched.geometry.intersects(polygon)

        matched_indices = matched[intersects].index

        trajectories.loc[matched_indices, 'area_id'] = area_id

    return trajectories



def quadrat_cut_geometry(geometry, quadrat_width, min_num=3, buffer_amount=1e-9):
    """
    Split a Polygon or MultiPolygon up into sub-polygons of a specified size, using quadrats.
		
	Parameters
	----------
	geometry : shapely Polygon or MultiPolygon
		the geometry to split up into smaller sub-polygons
	quadrat_width : numeric
		the linear width of the quadrats with which to cut up the geometry (in the units the geometry is in)
	min_num : int
		the minimum number of linear quadrat lines (e.g., min_num=3 would produce a quadrat grid of 4 squares)
	buffer_amount : numeric
		buffer the quadrat grid lines by quadrat_width times buffer_amount
	
	Returns
	-------
	shapely MultiPolygon
    """
    
	# Create n evenly spaced points between the min and max x and y bounds
    
    west, south, east, north = geometry.bounds
    x_num = int(np.ceil((east - west) / quadrat_width)) + 1
    y_num = int(np.ceil((north - south) / quadrat_width)) + 1
    x_points = np.linspace(west, east, max(x_num, min_num))
    y_points = np.linspace(south, north, max(y_num, min_num))

    # Create a quadrat grid of lines at each of the evenly spaced points
    vertical_lines = [shapely.geometry.LineString([(x, y_points[0]), (x, y_points[-1])]) for x in x_points]
    horizontal_lines = [shapely.geometry.LineString([(x_points[0], y), (x_points[-1], y)]) for y in y_points]

    lines = vertical_lines + horizontal_lines

    # buffer each line to distance of the quadrat width divided by 1 billion,
	# take their union, then cut geometry into pieces by these quadrats
    buffer_size = quadrat_width * buffer_amount
    lines_buffered = [line.buffer(buffer_size) for line in lines]
    quadrats = shapely.ops.unary_union(lines_buffered)

    # Cut the geometry
    multipoly = geometry.difference(quadrats)

    return multipoly
