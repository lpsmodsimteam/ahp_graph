#
# This module defines simple methods for reading and merging datasheets.
# A datasheet is represented as a JSON-compatible Python structure.
#

import collections
import copy
import io
import re

import orjson
import numexpr # type: ignore[import]

__all__ = [ "load", "merge" ]

def load(filename):
	"""
	Load a datasheet.  Filter comments and apply a simple recursive
	math function to evaluate expressions.
	"""
	with io.open(filename, 'r') as dfile:
		lines = [re.sub('//.*', '', line) for line in dfile]
	datasheet = orjson.loads(" ".join(lines))
	__recurse_math_expr(datasheet)
	return datasheet

def __recurse_math_expr(dict_like):
	"""
	Iterate over the database and replace all strings that start
	with "=" with a scalar by evaluating the substring following
	the equals.  Recurse if the database entry is a dictonary-like
	object.
	"""
	for (key,val) in dict_like.items():
		if isinstance(val, str) and re.match(r'=[^=]', val):
			dict_like[key] = float(numexpr.evaluate(val[1:].strip()))
		elif isinstance(val, collections.Mapping):
			__recurse_math_expr(val)

def merge(ds1, ds2):
	"""
	Return the merge of two data sheets.
	"""
	ds = copy.deepcopy(ds1)

	for dtype in ds2:
		if dtype not in ds:
			ds[dtype] = copy.deepcopy(ds2[dtype])
		else:
			for (model,data) in ds2[dtype].items():
				ds[dtype][model] = copy.deepcopy(data)

	return ds
