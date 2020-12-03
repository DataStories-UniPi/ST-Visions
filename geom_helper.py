'''
	geom_helper.py - v2020.05.07

	Authors: Andreas Tritsarolis, Christos Doulkeridis, Yannis Theodoridis and Nikos Pelekis

	Notes:	
		* The Methods ```getXYCoords```, ```getPolyCoords```, ```getLineCoords```, ```getPointCoords```, ```multiGeomHandler``` and ```getCoords``` were forked from: Advanced plotting with Bokeh, https://automating-gis-processes.github.io/2017/lessons/L5/advanced-bokeh.html, Last visited at: 09/03/2020.
		* The Method ```quadrat_cut_geometry``` was forked from: https://github.com/gboeing/osmnx/blob/f5eb1fc4f18c1816987de7f0db8d35690dc65f41/osmnx/core.py#L589, Last visited at: 12/03/2020.
'''


import shapely
import numpy as np
from tqdm import tqdm 
import geopandas as gpd


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
	return geometry.coords.xy[coord_index]


def getPolyCoords(geometry, coord_index, complex_geom):
	""" 
	Returns Coordinates of Polygon using the Exterior of the Polygon.
	"""
	ext = geometry.exterior

	exterior_coords = np.array(getXYCoords(ext, coord_index))

	if complex_geom:    
		interior_coords = []

		for interior in geometry.interiors:
			interior_coords += [np.array(getXYCoords(interior, coord_index))]

		return [{'exterior': np.array(exterior_coords), 'holes':np.array(interior_coords)}]
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
	return getXYCoords(geometry, coord_index)


def multiGeomHandler(multi_geometry, coord_index, geom_type, complex_geom=False):
	"""
	Function for handling multi-geometries. Can be MultiPoint, MultiLineString or MultiPolygon.
	Returns a list of coordinates where all parts of Multi-geometries are merged into a single list.
	Individual geometries are separated with np.nan which is how Bokeh wants them.
	
	Bokeh documentation regarding the Multi-geometry issues can be found here (it is an open issue) - https://github.com/bokeh/bokeh/issues/2321
	"""
	for i, part in enumerate(multi_geometry):
		# On the first part of the Multi-geometry initialize the coord_array (np.array)
		if i == 0:
			if geom_type == "MultiPoint":
				coord_arrays = np.append(getPointCoords(part, coord_index), np.nan)
			elif geom_type == "MultiLineString":
				coord_arrays = np.append(getLineCoords(part, coord_index), np.nan)
			elif geom_type == "MultiPolygon":
				if complex_geom:
					coord_arrays = [getPolyCoords(part, coord_index, complex_geom)]
				else:
					coord_arrays = np.append(getPolyCoords(part, coord_index, complex_geom), np.nan)
		else:
			if geom_type == "MultiPoint":
				coord_arrays = np.concatenate([coord_arrays, np.append(getPointCoords(part, coord_index), np.nan)])
			elif geom_type == "MultiLineString":
				coord_arrays = np.concatenate([coord_arrays, np.append(getLineCoords(part, coord_index), np.nan)])
			elif geom_type == "MultiPolygon":
				if complex_geom:
					coord_arrays += [getPolyCoords(part, coord_index, complex_geom)]
				else:
					coord_arrays = np.concatenate([coord_arrays, np.append(getPolyCoords(part, coord_index, complex_geom), np.nan)])

	if geom_type == "MultiPolygon" and complex_geom:
		coord_arrays = np.array(concatPolyCoords(coord_arrays)).reshape(1,-1)

	# Return the coordinates
	return coord_arrays


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
		Either List (in case of Point, Line or Polygon geometries) or Nested List (in case of MultiPoint, MultiLineString or MultiPolygon geometries)
	"""
	# Check the geometry type
	gtype = geom.geom_type

	# "Normal" geometries
	# -------------------
	if gtype == "Point":
		# print (f'Point: {getPointCoords(geom, coord_index)}')
		return getPointCoords(geom, coord_index)[0]
	elif gtype == "LineString":
		# print (f'LineString: {getLineCoords(geom, coord_index)}')
		return np.array(getLineCoords(geom, coord_index))
	elif gtype == "Polygon":
		# print (f'Polygon: {getPolyCoords(geom, coord_index)}')
		poly_coords = getPolyCoords(geom, coord_index, complex_geom)

		if complex_geom:
			return np.array(concatPolyCoords([poly_coords])[0])
		else:
			return poly_coords

	# Multi geometries
	# ----------------
	else:
		return np.array( multiGeomHandler(geom, coord_index, gtype) )


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
	
	name = gdf.geometry.name
	linestrings = gdf.groupby(column_handlers, group_keys=False).progress_apply(lambda l: shapely.geometry.LineString(l[name].values) if len(l) >= 2 else shapely.geometry.LineString(np.repeat(l[name].values, 2))).to_frame().reset_index()
	linestrings.rename({0: 'geom'}, inplace=True, axis=1)
	linestrings = gpd.GeoDataFrame(linestrings, crs=gdf.crs, geometry='geom')

	return linestrings


def getGeoDataFrame_v2(df, coordinate_columns=['lon', 'lat'], crs={'init':'epsg:4326'}):
	'''
		Create a GeoDataFrame from a DataFrame in a much more generalized form.
	'''
	
	df.loc[:, 'geom'] = np.nan
	df.geom = df[coordinate_columns].apply(lambda x: shapely.geometry.Point(*x), axis=1)
	
	return gpd.GeoDataFrame(df, geometry='geom', crs=crs)


def classify_area_proximity(trajectories, spatial_areas, compensate=False, buffer_amount=1e-14, verbose=True):
	"""
	Classify Point Geometries according to their Spatial Proximity to one (or many) Spatial Area(s).

	Parameters
	----------
	trajectories: GeoPandas GeoDataFrame
		Contains information about the Point Geometries
	spatial_areas: GeoPandas GeoDataFrame
		Contains information about the Spatial Areas
	compensate: Boolean (default: False)
		Buffer each spatial area by ```buffer_ammount```
	buffer_ammount: Numeric (default: 1e-14)
		Buffer ammount for ```spatial_areas``` (if ```compensate = True```)
	verbose: Boolean (default: True)
		Enable/Disable Verbosity

	Returns
	-------
	GeoPandas GeoDataFrame
	"""

	# create the spatial index (r-tree) of the trajectories's data points
	print ('Creating Spatial Index...') if verbose else None
	sindex = trajectories.sindex

	print ('Classifying Spatial Proximity...') if verbose else None
	for area_id, poly in tqdm(spatial_areas.geometry.items(), disable=not verbose):
		if compensate:
			poly = poly.buffer(buffer_amount).buffer(0)

		possible_matches_index = list(sindex.intersection(poly.bounds))
		possible_matches = trajectories.iloc[possible_matches_index]
		precise_matches = possible_matches[possible_matches.intersects(poly)]
		
		if (len(precise_matches) != 0):
			trajectories.loc[precise_matches.index, 'area_id'] = area_id
		
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
	
	# create n evenly spaced points between the min and max x and y bounds
	west, south, east, north = geometry.total_bounds
	x_num = int(np.ceil((east-west) / quadrat_width) + 1)
	y_num = int(np.ceil((north-south) / quadrat_width) + 1)
	x_points = np.linspace(west, east, num=max(x_num, min_num))
	y_points = np.linspace(south, north, num=max(y_num, min_num))

	# create a quadrat grid of lines at each of the evenly spaced points
	vertical_lines = [shapely.geometry.LineString([(x, y_points[0]), (x, y_points[-1])]) for x in x_points]
	horizont_lines = [shapely.geometry.LineString([(x_points[0], y), (x_points[-1], y)]) for y in y_points]
	lines = vertical_lines + horizont_lines

	# buffer each line to distance of the quadrat width divided by 1 billion,
	# take their union, then cut geometry into pieces by these quadrats
	buffer_size = quadrat_width * buffer_amount
	lines_buffered = [line.buffer(buffer_size) for line in lines]
	quadrats = shapely.ops.unary_union(lines_buffered)
	multipoly = geometry.difference(quadrats)

	return multipoly
