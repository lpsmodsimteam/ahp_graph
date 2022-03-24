#
# This module defines the geometry object describing Devices
# A geometry contains the following information:
#   * plane:  one of the z plotting planes
#   * shape:  either LineShape or PolygonShape
#   * color:  color understood by matplotlib
#   * offset: (x,y) offset
#   * scale:  (x,y) scale factors
#   * rot:    shape rotation in degrees
#
# The shape is rotated, scaled, and then offset.  If either
# the shape or color is not provided, then it is taken from
# the default datasheet.
#

import io
import json
import math
import matplotlib # type: ignore[import]
import os
import re

if 'DISPLAY' not in os.environ:
	matplotlib.use("Agg")

from matplotlib import figure, pyplot # type: ignore[import,attr-defined]
from matplotlib.lines import Line2D # type: ignore[import]
from matplotlib.patches import PathPatch # type: ignore[import]
from matplotlib.path import Path # type: ignore[import]

__all__ = [ "Geometry", "LineShape", "PolygonShape" ]

#
# A LineShape is rendered as a set of points connected by a line.
#
class LineShape:
	def __init__(self, points, color=None):
		self.stype  = "Line"
		self.points = points
		self.color  = color

#
# A PolygonShape is rendered as a closed polygon described by a
# series of points.  The first and last points must be the same.
#
class PolygonShape:
	def __init__(self, points, color=None):
		self.stype  = "Polygon"
		self.points = points
		self.color  = color

#
# The geometry class describes the geometry of a single Device.
# Shape attributes not specified in the constructor are taken
# from the Device database. The geometry is plotted using matplotlib.
#
class Geometry:

	#
	# Create a geometry object.  The geometry is defined by the plane,
	# shape, color, offset, scale, and rot.  The offset is required.
	# If not provided, the plane defaults to zero, the shape defaults
	# to the datasheet shape, the color defaults to the datasheet color,
	# the scale defaults to (1,1), and the rotation defaults to zero.
	#
	def __init__(self, offset, shape, **kwargs):
		self.offset = offset
		self.shape  = shape
		self.plane  = kwargs.get('plane', 0)
		self.color  = kwargs.get('color')
		self.scale  = kwargs.get('scale', 1.0)
		self.rot    = kwargs.get('rot', 0)

		if self.color is None:
			self.color = shape.color if shape.color is not None else "black"
		if isinstance(self.scale, (int,float)):
			self.scale = (self.scale, self.scale)

		#
		# Generate the points for this geometry object by applying
		# the transformation matrix to the shape points in the order
		# (1) rotation, (2) scaling, and (3) offset.
		#
		(dx,dy)  = self.offset
		(sx,sy)  = self.scale
		rot      = math.radians(self.rot)
		A        = sx*math.cos(rot)
		B        = -sx*math.sin(rot)
		C        = sy*math.sin(rot)
		D        = sy*math.cos(rot)
		self.pts = [(A*x+B*y+dx,C*x+D*y+dy) for (x,y) in self.shape.points]

	def __str__(self):
	  return f'o:{self.offset},s:{self.shape},p:{self.plane},c:{self.color},sc:{self.scale},r:{self.rot}:p:{self.pts}'

	#
	# Lookup shape and color information from the datasheet and
	# return the appropriate shape.
	#
	@staticmethod
	def DataSheetShape(dtype, model, datasheet):
		if dtype not in datasheet:
			raise RuntimeError(f"Unknown Geometry for device: {dtype}")
		if model not in datasheet[dtype]:
			raise RuntimeError(f"Unknown device model: {dtype}/{model}")

		info = datasheet[dtype][model]
		if 'shape' not in info:
			raise RuntimeError(f"No shape information: {dtype}/{model}")

		stype  = info['shape'][0]
		color  = info.get('color')
		points = info['shape'][1:]

		if stype == "Line":
			return LineShape(points, color)
		elif stype == "Polygon":
			return PolygonShape(points, color)
		else:
			raise RuntimeError(f"Unknown shape: {stype}")

	#
	# Plot the devices in the graph using matplotlib.  Show the plot
	# if show is true.  If figfile is provided, then write the image
	# to that file.  If figsize is provided, then set the size of the
	# figure to (w,h) in inches.
	#
	@staticmethod
	def plot(graph, title=None, show=True, figfile=None, figsize=None):

		#
		# Calculate the number of planes.
		#
		planes = 1
		for device in graph.devices():
			if 'geometry' in device.attr:
				planes = max(planes, device.attr['geometry'].plane+1)

		#
		# Use matplotlib to create the figure and axes.  We place the
		# two axes next to each other so plot with the same Y values.
		# Also ensure the X axes are the same to maintain the aspect
		# ratio.
		#
		if planes == 1:
			fig, ax = pyplot.subplots(figsize=figsize)
			ax = [ ax ]
		else:
			if figsize is None:
				figsize = figure.figaspect(1.0/planes)
			fig, ax = pyplot.subplots(
				1, planes,
				figsize=figsize,
				sharex=True,
				sharey=True
			)

		#
		# Now plot the devices on the different planes.
		#
		for device in graph.devices():
			if 'geometry' in device.attr:
				geom = device.attr['geometry']

				if geom.shape.stype == "Line":
					x = [pt[0] for pt in geom.pts],
					y = [pt[1] for pt in geom.pts],
					line = Line2D(x, y, color=geom.color)
					ax[geom.plane].add_line(line)
				elif geom.shape.stype == "Polygon":
					n = len(geom.pts)
					codes = [ Path.MOVETO ]
					codes.extend((n-2) * [ Path.LINETO ])
					codes.extend([ Path.CLOSEPOLY ])
					path = Path(geom.pts, codes)
					poly = PathPatch(path, color=geom.color)
					ax[geom.plane].add_patch(poly)
				else:
					raise RuntimeError(f"Unknown shape: {geom.shape.stype}")

		#
		# Save and/or show the result
		#
		fig.suptitle(title if title is not None else "Device Geometry")
		for a in ax:
			a.axis('scaled')

		if figfile:
			pyplot.savefig(figfile)
		if show:
			pyplot.show()

	#
	# Write the device geometry information to the specified JSON file.
	#
	@staticmethod
	def write(filename, graph):
		config = dict()

		for device in graph.devices():
			if 'geometry' in device.attr:
				geom = device.attr['geometry']
				config[device.name] = {
					"shape"  : geom.shape.stype,
					"device_center" : (geom.offset[0], geom.offset[1], geom.plane),
					"center_point"  : geom.offset,
					"points" : geom.pts,
					"plane"  : geom.plane,
					"color"  : geom.color
				}

		with io.open(filename, 'w') as jfile:
			json.dump(config, jfile, indent=2, sort_keys=True)

	#
	# Plot the JSON file.
	#
	@staticmethod
	def plotjson(jsonfile, title=None, show=True, figfile=None, figsize=None):

		#
		# Pull in the device plotting information from the JSON file.
		#
		with io.open(jsonfile, 'r') as jfile:
			devices = json.load(jfile)

		#
		# Use matplotlib to create the figure and axes.  We place the
		# two axes next to each other so plot with the same Y values.
		# Also ensure the X axes are the same to maintain the aspect
		# ratio.
		#
		planes = max([device['plane']+1 for device in devices.values()])
		if planes == 1:
			fig, ax = pyplot.subplots(figsize=figsize)
			ax = [ ax ]
		else:
			if figsize is None:
				figsize = figure.figaspect(1.0/planes)
			fig, ax = pyplot.subplots(
				1, planes,
				figsize=figsize,
				sharex=True,
				sharey=True)

		#
		# Now plot the devices on the different planes.
		#
		for device in devices.values():
			if device['shape'] == "Line":
				x = [pt[0] for pt in device['points']],
				y = [pt[0] for pt in device['points']],
				line = Line2D(x, y, color=device['color'])
				ax[device['plane']].add_line(line)
			else:
				n = len(device['points'])
				codes = [ Path.MOVETO ]
				codes.extend((n-2) * [ Path.LINETO ])
				codes.extend([ Path.CLOSEPOLY ])
				path = Path(device['points'], codes)
				poly = PathPatch(path, color=device['color'])
				ax[device['plane']].add_patch(poly)

		#
		# Save and/or show the result
		#
		fig.suptitle(title if title is not None else jsonfile)
		for a in ax:
			a.axis('scaled')

		if figfile:
			pyplot.savefig(figfile)
		if show:
			pyplot.show()
