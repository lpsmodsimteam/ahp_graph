#
# This module implements support for AHP (attributed hierarchical port)
# graphs of devices and their port-based connections.  This class of graphs
# support attributes on the nodes (devices), links that are connected to
# named ports on the nodes, and the non-simple nodes that may be represented
# by a hierarchical graph (aka an assembly).  All links are unidirectional.
#

import collections
import io
import types

__all__ = [
	"assembly",
	"Device",
	"DeviceGraph",
	"Port",
	"ExternalPort",
	"port",
	"sstlib"
]

#
# The Port namespace defines constants used to describe ports.
#
Port = types.SimpleNamespace(

	#
	# Port cardinality: single, multi, or bounded(N).
	#
	Single  = -1,
	Multi   = 0,
	Bounded = lambda x : x,

	#
	# Whether the port is optional or required.
	#
	Optional = False,
	Required = True,

	#
	# Define common port types for checking port compatibility.
	# Each of these ends in an implicit message in SST.
	#
	Analog  = "Analog",
	Digital = "Digital"
)

#
# Decorator syntactic suger to define the SST component associated
# with a device.  This makes the device definitions look a little
# prettier.  Note that a node may have an SST attribute and also
# be an assembly (e.g., a multi-resolution model of a component).
#
def sstlib(name):
	def wrapper(cls):
		cls.sstlib = name
		return cls
	return wrapper

#
# Decorator syntactic sugar to indicate that a device is an assembly.
# Verify that there is an expand method.
#
def assembly(cls):
	if not hasattr(cls, "expand"):
		raise RuntimeError(f"Assemblies must define expand(): {cls.__name__}")
	cls.assembly = True
	return cls

#
# Decorator syntactic sugar to define the ports for a particular device.
# A port is defined by a name, cardinality (single, multiple, or bounded),
# a port type (a string or None), and whether it is required.
#
def port(name, card, ptype=None, need=Port.Optional):
	def wrapper(cls):
		if not hasattr(cls, "_portlist"):
			cls._portlist = list()
			cls._porttype = dict()
			cls._portcard = dict()
			cls._portneed = dict()
		cls._portlist.insert(0, (name, card, ptype, need))
		cls._portcard[name] = card
		cls._porttype[name] = ptype
		cls._portneed[name] = need
		return cls
	return wrapper

#
# A DevicePort object contains a device reference, a port name, and an
# optional port number.
#
class DevicePort:
	def __init__(self, device, name, number=None):
		self.device = device
		self.name   = name
		self.number = number

	def is_single(self):
		return self.number is None

	def __repr__(self):
		if self.number is None:
			return f"{self.device.name}.{self.name}"
		else:
			return f"{self.device.name}.{self.name}.{self.number}"

	def __lt__(self, other):
		n0 = -1 if self.number is None else self.number
		n1 = -1 if other.number is None else other.number
		p0 = (self.device.name,  self.name,  n0)
		p1 = (other.device.name, other.name, n1)
		return p0 < p1

#
# A ExternalPort object contains an sst.Component and a port name.
#
class ExternalPort:
	def __init__(self, comp, portName):
		self.comp = comp
		self.portName = portName

	def __repr__(self):
		return f"{self.comp.getFullName()}.{self.portName}"

	def comp_name(self):
		return self.comp.getFullName()

	def port_name(self):
		return self.portName

#
# Device is the base class for a node in the AHP graph.  This object
# is immutable.  Each device exports several ports.  A device may be
# represented by an SST component, may be an assembly of other devices,
# or both.  If an assembly, then the device must define an expand()
# method that returns a device graph that implements the device.
#
# Note that successive calls to port() will return the same DevicePort
# object so they can be used in sets and comparisons.
#
# Each device must have a unique name and model.
#
class Device:
	sstlib   = None
	assembly = False

	#
	# Initialize the device with the unique name, model, and optional
	# dictionary of attributes (typically from kwargs).
	#
	def __init__(self, name, model, attr=None):
		self.name      = name
		self.attr      = dict(attr) if attr is not None else dict()
		self._ports    = collections.defaultdict(dict)
		self._nport    = collections.defaultdict(int)
		self._sub      = list()
		self._issub    = False
		self._subOwner = None

		self._rank   = None
		self._thread = None

		self.attr['model'] = model
		self.attr['type']  = self.__class__.__name__

	#
	# Assign a rank and optional thread to this device.
	#
	def set_partition(self, rank, thread=0):
		self._rank = rank
		self._thread = thread

	#
	# Add a subcomponent to this component.  Both the subcomponent and
	# this component must be SST classes.  Note that all subcomponents
	# must be added to the device before the device is added to the graph.
	#
	def add_subcomponent(self, device, name, slot):
		if self.sstlib is None:
			raise RuntimeError(f"Parent of sub-component must be an SST class")
		if device.sstlib is None:
			raise RuntimeError(f"A sub-component must be an SST class")
		device._issub = True
		device._subOwner = self
		self._sub.append((device, name, slot))

	#
	# Return whether this component is a subcomponent.
	#
	def is_subcomponent(self):
		return self._issub

	#
	# Return the list of (device,slot) sub-component pairs.
	#
	def get_subcomponents(self):
		return self._sub

	#
	# As a convenience, we allow ports to be named as an attribute on the
	# class (e.g., awg.DigitalInput instead of awg.port("DigitalInput").
	# If the port is not defined, then we thrown an exception.
	#
	def __getattr__(self, port):
		card = self._portcard.get(port)

		if card is None:
			raise RuntimeError(f"Unknown port in {self.name}: {port}")
		elif card == Port.Single:
			return self.port(port)
		else:
			return lambda x : self.port(port, x)

	#
	# Return a Port object representing the port on this device.
	#
	# If a Single port, then make sure we do not have a port number.
	# If the port has not already been defined, then add it.
	#
	# If a Bounded or Multi port, determine the port number.  If
	# number is None, then create a new port at the end of the current
	# list.  Make sure we do not create too many connections if Bounded.
	# Finally, if the port has not already been defined, then create it.
	#
	def port(self, port, number=None):
		portcard = self._portcard.get(port)

		if portcard is None:
			raise RuntimeError(f"Unknown port in {self.name}: {port}")

		elif portcard == Port.Single:
			if number is not None:
				raise RuntimeError(f"Port supports one connection: {port}")
			if port not in self._ports:
				self._ports[port] = DevicePort(self, port)
			return self._ports[port]

		else:
			if number is None:
				number = self._nport[port]
				self._nport[port] += 1
			else:
				self._nport[port] = number + 1
			if portcard != Port.Multi and number >= portcard:
				raise RuntimeError(f"Too many connections: {port}")
			if number not in self._ports[port]:
				self._ports[port][number] = DevicePort(self, port, number)
			return self._ports[port][number]

	#
	# Reset the port count for multiports.
	#
	def reset_port_count(self):
		for port in self._nport:
			self._nport[port] = 0

	#
	# Return a description of the Device.
	#
	def __repr__(self):
		lines = list()
		lines.append(f"Device={self.__class__.__name__}")
		lines.append(f"    name={self.name}")
		lines.append(f"    is-assembly={self.assembly}")

		if self.sstlib is not None:
			lines.append(f"    sstlib={self.sstlib}")

		for key in sorted(self.attr):
			lines.append(f"    {key}={self.attr[key]}")
		return "\n".join(lines)

#
# A DeviceGraph is a graph of devices and their connections to one
# another.  The devices are nodes and the links connect the ports on
# the nodes.  This implements an AHP (annotated hierarchical port)
# graph.
#
class DeviceGraph:

	#
	# Define an empty device graph.  The attributes are considered
	# global parameters shared by all instances in the graph.  They
	# are only supported at the top-level graph, not intemediate
	# graphs (e.g., assemblies).
	#
	def __init__(self, attr=None):
		self.attr = dict(attr) if attr is not None else dict()

		self._names     = set()
		self._devicemap = dict()
		self._devices   = set()
		self._linkset   = set()
		self._linklist  = list()
		self._linkmap   = collections.defaultdict(set)
		self._ports     = set()

		#
		# Ports outside the graph and links to them.
		#
		self._extnames = set()
		self._extports = set()
		self._extlinkset = set()

	#
	# Pretty print graph with devices followed by links.
	#
	def __repr__(self):
		lines = list()
		for device in sorted(self._devices, key=lambda d : d.name):
			lines.append(str(device))
		for (p0,p1) in self._linkset:
			lines.append(f"{p0} <---> {p1}")
		for (p0,p1) in self._extlinkset:
			lines.append(f"{p0} <---> {p1}")
		return "\n".join(lines)

	#
	# Set the shared configuration file attribute.
	#
	def set_config(self, config):
		self.attr['SharedConfig'] = config

	#
	# Add a node to the device graph.  The node may be a Device or
	# SST Component.  The name must be unique.  If the device has
	# sub-components, then we add those, as well.  Do NOT add
	# sub-components to a device after you have added it using
	# this function.  Add sub-components first, then add the parent.
	#
	def add(self, node):
		if isinstance(node, Device):
			if node.name in self._names or node.name in self._extnames:
				raise RuntimeError(f"Name already in graph: {node.name}")
			self._names.add(node.name)
			self._devices.add(node)
			self._devicemap[node.name] = node
			for (d,_,_) in node.get_subcomponents():
				self.add(d)
		else:
			name = node.getFullName()
			if name in self._extnames or name in self._names:
				raise RuntimeError(f"Name already in graph: {name}")
			self._extnames.add(name)

	#
	# Return a particular device by name.
	#
	def device(self, name):
		return self._devicemap[name]

	#
	# Return an iterator over the devices in the graph.
	#
	def devices(self):
		return iter(self._devices)

	#
	# Return an iterator over the external components in the graph.
	#
	def ext_comps(self):
		return iter(self._extnames)

	#
	# Return an iterator over the port links in the graph.  The
	# list is a tuple of the form (p0,p1,t) for port p0, port p1,
	# and link time t.
	#
	def links(self):
		return iter(self._linklist)

	#
	# Return an iterator over the external port links in the graph.
	#
	def ext_links(self):
		return iter(self._extlinkset)

	#
	# Return a link count for the specified port name on the device.
	#
	def count(self, device, port):
		links = self._linkmap.get(device)
		if links is None:
			raise RuntimeError(f"Device {device.name} not in graph")
		return len([1 for (p0,p1) in links if p0.name == port])

	#
	# Link two ports on two different devices.  Links are undirected,
	# so we normalize the link direction by the names of the two device
	# endpoints.  If any of the devices associated with the link are not
	# in the graph or the link types to not match, then throw an exception.
	#
	# The time t is given in picoseconds.  The default value, zero, means
	# "as fast as possible" (typically 1 ps).
	#
	def link(self, p0, p1, t=0):
		if type(p0) is tuple:
			self.link_external(p1, ExternalPort(*p0))
			return

		if type(p1) is tuple:
			self.link_external(p0, ExternalPort(*p1))
			return

		if callable(p0) or callable(p1):
			print(f"WARNING: You sent a callable object to link().  This will probably result in an error next.")
			print(f"By the way if you are calling link() with a Multi type port and you didn't select an index this will happen.")
			print(f"You might want to pass in: dev.Input(0) or dev.Input(None) where None indicates use the next port.")

		if p0.device is None:
			raise RuntimeError(f"Bad link arg0: {p0}")
		if p1.device is None:
			raise RuntimeError(f"Bad link arg1: {p1}")

		if p0.device.name > p1.device.name:
			(p0,p1) = (p1,p0)
		if (p0,p1) in self._linkset:
			raise RuntimeError(f"Link already in graph: {p0} <---> {p1}")

		if p0 in self._ports:
			raise RuntimeError(f"Port already in graph: {p0}")
		if p1 in self._ports:
			raise RuntimeError(f"Port already in graph: {p1}")
		self._ports.add(p0)
		self._ports.add(p1)

		d0 = p0.device
		d1 = p1.device

		if d0 not in self._devices:
			raise RuntimeError(f"Device name not in graph: {d0.name}")
		if d1 not in self._devices:
			raise RuntimeError(f"Device name not in graph: {d1.name}")

		t0 = d0._porttype[p0.name]
		t1 = d1._porttype[p1.name]

		if t0 != t1:
			raise RuntimeError(f"Port type mismatch: {t0} != {t1} between {d0.name} and {d1.name}")

		self._linkset.add((p0,p1))
		self._linklist.append((p0,p1,t))

	#
	# Similar to link(), but p1 is an ExternalPort (comp, portName)
	# instead of a DevicePort.  comp is an SST component not managed
	# by PyDL.  This is how we link a PyDL Device to an SST component
	# that isn't PyDL-managed.
	#
	def link_external(self, p0, p1):
		if p1.comp_name() not in self._extnames:
			self._extnames.add(p1.comp_name())

		if (p0,p1) in self._extlinkset:
			raise RuntimeError(f"Link already in graph: {p0} <---> {p1}")

		if p0 in self._ports:
			raise RuntimeError(f"Port already in graph: {p0}")
		if p1 in self._extports:
			raise RuntimeError(f"Port already in graph: {p1}")

		self._ports.add(p0)
		self._extports.add(p1)
		self._extlinkset.add((p0,p1))

	#
	# Verify that all required ports are linked up.  Throw an exception
	# if there is an error.
	#
	def verify_links(self):

		#
		# Create a map of devices to all ports linked on those devices.
		#
		d2ports = collections.defaultdict(set)
		for (p0,p1) in self._linkset:
			d2ports[p0.device].add(p0.name)
			d2ports[p1.device].add(p1.name)
		for (p0,_) in self._extlinkset:
			d2ports[p0.device].add(p0.name)

		#
		# Walk all devices and make sure required ports are connected.
		#
		for device in self._devices:
			for (name, _, _, need) in device._portlist:
				if need and name not in d2ports[device]:
					raise RuntimeError(f"{device.name} requires port {name}")

	#
	# Given a graph, follow links from the specified rank and expand assemblies
	# until links are fully defined (links touch sstlib Devices on both sides)
	#
	def follow_links(self, rank):
		graph = self
		while True:
			devices = set()
			for (p0, p1) in graph._linkset:
				# one of the devices is on the rank that we are following links on
				if p0.device._rank == rank or p1.device._rank == rank:
					for p in [p0, p1]:
						if p.device.sstlib is None:
							# link on the rank we want, device needs expanded
							devices.add(p.device)
			if devices:
				graph = graph.flatten(1, expand=devices)
			else:
				break
		return graph

	#
	# Recursively flatten the graph by the specified number of levels.
	# For example, if levels is one, then only one level of the hierarchy
	# will be expanded.  If levels is None, then the graph will be fully
	# expanded.  If levels is zero or no devices are an assembly, then just
	# return self.
	#
	# The name parameter lets you flatten the graph only under a specified
	# device. If the assemblies keep the name of the parent for the devices
	# in the expanded graph as a prefix, this expansion allows for multi-level
	# expansion of an assembly of assemblies.  The deliminter must be a '.'
	# for the name to function, e.g., Assembly.subassembly.device.
	#
	# The rank parameter lets you flatten the graph for all devices in the
	# specified rank
	#
	# You can also provide a set of devices to expand instead of looking
	# through the entire graph
	#
	def flatten(self, levels=None, name=None, rank=None, expand=None):
		# Build up a list of devices that don't need expanded
		# and a list of devices to be expanded
		#
		# non-assembly devices automatically are added to the devices list
		# Devices must have a matching name if provided, a matching
		# rank if provided, and be within the expand set if provided
		# if they are to be added to the assemblies list of devices to expand
		devices = list()
		assemblies = list()

		if name is not None:
			splitName = name.split('.')

		for dev in self._devices:
			assembly = dev.assembly

			# check to see if the name matches
			if name is not None:
				assembly &= (splitName == dev.name.split('.')[0:len(splitName)])
			# rank to check
			if rank is not None:
				assembly &= (rank == dev._rank)
			# check to see if the device is in the expand set
			if expand is not None:
				assembly &= (dev in expand)

			if assembly:
				assemblies.append(dev)
			else:
				devices.append(dev)

		if levels == 0 or not assemblies:
			return self

		#
		# Start by creating a link map.  This will allow us quick lookup
		# of the links in the graph.  We add both directions, since we will
		# need to look up by both the first and second device.
		#
		links = collections.defaultdict(set)
		for (p0, p1) in self._linkset:
			links[p0.device].add((p0,p1))
			links[p1.device].add((p1,p0))
		for (p0, p1) in self._extlinkset:
			links[p0.device].add((p0,p1))

		linktimes = dict()
		for (p0, p1, t) in self._linklist:
			linktimes[(p0,p1)] = t
			linktimes[(p1,p0)] = t

		#
		# Expand the required devices
		#
		for device in assemblies:
			device.reset_port_count()
			subgraph = device.expand()

			#
			# Update the list of devices from the subgraph.  We
			# throw away the node we just expanded.  Expanded
			# devices inherit the partition of the parent.
			#
			for d in subgraph.devices():
				if d != device and not d.is_subcomponent():
					d._rank = device._rank
					d._thread = device._thread
					devices.append(d)

			#
			# Define a subroutine to find the matching port and
			# remove the associated link.  If we were not able to
			# find a matching port, then return None.
			#
			def find_other_port(port):
				for (p0,p1) in links[port.device]:
					if p0 == port:
						links[p0.device].remove((p0,p1))
						if type(p1) is DevicePort:
							links[p1.device].remove((p1,p0))
						return p1
				return None

			#
			# Update the links
			# For debugging, it helps to sort the subgraphLinks
			# to get a deterministic order.
			#
			subgraphLinks = subgraph.links()
			# subgraphLinks = sorted(subgraphLinks)
			for (p0,p1,t) in subgraphLinks:
				if p0.device == device:
					p2 = find_other_port(p0)
					if p2 is not None:
						linktimes[(p1,p2)] = linktimes.get((p0,p2), 0) + t
						linktimes[(p2,p1)] = linktimes.get((p0,p2), 0) + t
						links[p1.device].add((p1,p2))
						if type(p2) is DevicePort:
							links[p2.device].add((p2,p1))
				elif p1.device == device:
					p2 = find_other_port(p1)
					if p2 is not None:
						linktimes[(p0,p2)] = linktimes.get((p1,p2), 0) + t
						linktimes[(p2,p0)] = linktimes.get((p1,p2), 0) + t
						links[p0.device].add((p0,p2))
						if type(p2) is DevicePort:
							links[p2.device].add((p2,p0))
				else:
					linktimes[(p0,p1)] = t
					linktimes[(p1,p0)] = t
					links[p0.device].add((p0,p1))
					links[p1.device].add((p1,p0))

			#
			# Sanity check that we removed all the links
			#
			for (p0,p1) in links[device]:
				raise RuntimeError(f"Unexpanded port: {p0}, {p1}")

		#
		# Reconstruct the new graph from the devices and links.
		#
		graph = DeviceGraph(self.attr)

		for device in devices:
			graph.add(device)

		for linkset in links.values():
			for (p0,p1) in linkset:
				if type(p1) is ExternalPort:
					graph.link_external(p0, p1)
				elif p0.device.name < p1.device.name:
					graph.link(p0, p1, linktimes[(p0,p1)])

		#
		# Recursively flatten
		#
		return graph.flatten(None if levels is None else levels-1, name, rank, expand)

	#
	# Count the devices in a graph.  Return a map of components to integer
	# counts.  The keys are of the form (CLASS,MODEL,LEVEL).  If LEVEL is
	# not defined for the device, then it is None.
	#
	def count_devices(self):
		counter = collections.defaultdict(int)
		for device in self._devices:
			dtype = device.attr['type']
			model = device.attr['model']
			level = device.attr.get('level')
			counter[(dtype,model,level)] += 1
		return counter

	#
	# Write the device graph as a DOT file.
	#
	def write_dot_file(self, filename, title="Device Graph"):
		devices  = list(sorted(self._devices, key=lambda d : d.name))
		extcomps = list(sorted(self._extnames))
		d2n      = dict([(d,f"n{n}") for (n,d) in enumerate(devices+extcomps)])

		with io.open(filename, 'w') as gvfile:
			print(f"graph \"{title}\" {{", file=gvfile)

			for d0 in devices:
				n0 = d2n[d0]
				s0 = d0.name
				if 'model' in d0.attr:
					s0 += f"\\nmodel={d0.attr['model']}"
				if 'level' in d0.attr:
					s0 += f"\\nlabel={d0.attr['level']}"
				print(f"  {n0} [shape=box, label=\"{s0}\"];", file=gvfile)

			links = list()
			for (p0,p1) in self._linkset:
				links.append(f"{d2n[p0.device]} -- {d2n[p1.device]}")
			duplicates = collections.Counter(links)
			for key in duplicates:
				if duplicates[key] > 1:
					# more than one link going between components
					print(f"  {key} [label=\"{duplicates[key]}\"];", file=gvfile)
				else:
					# single link between components
					print(f"  {key};", file=gvfile)

			for c0 in extcomps:
				n0 = d2n[c0]
				print(f"  {n0} [shape=box, label=\"{c0}\"];", file=gvfile)

			links = list()
			for (p0,p1) in self._extlinkset:
				links.append(f"{d2n[p0.device]} -- {d2n[p1.comp_name()]}")
			duplicates = collections.Counter(links)
			for key in duplicates:
				if duplicates[key] > 1:
					# more than one link going between components
					print(f"  {key} [label=\"{duplicates[key]}\"];", file=gvfile)
				else:
					# single link between components
					print(f"  {key};", file=gvfile)

			print("}", file=gvfile)
