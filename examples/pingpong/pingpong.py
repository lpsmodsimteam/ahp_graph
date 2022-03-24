import os
import sys

from PyDL import *


# Ping Device
# Has a Name and a Model type
@sstlib("pingpong.Ping")
@port("inout", Port.Single)
class Ping(Device):
	def __init__(self, name, size, **kwargs):
		# size parameter is stored as the model attribute of a device
		super().__init__(name, size, kwargs)

# Pong Device
@sstlib("pingpong.Pong")
@port("inout", Port.Single)
class Pong(Device):
	def __init__(self, name, **kwargs):
		super().__init__(name, "Default", kwargs)


# Overall architecture layout
@assembly
class pingpong(Device):
	# size parameter is stored as the model attribute of a device
	def __init__(self, name, size = 10, **kwargs):
		super().__init__(name, size, kwargs)

	def expand(self):
		graph = DeviceGraph() # initialize a Device Graph
		graph.add(self) # add myself to the graph, useful if the assembly has ports

		ping = Ping("Ping", self.attr['model']) # create a Ping Device
		pong = Pong("Pong") # create a Pong Device

		# add ping and pong to the graph
		graph.add(ping)
		graph.add(pong)

		# link ping and pong
		graph.link(ping.inout, pong.inout)

		return graph


#
# If we are running as a script (either via Python or from SST), then
# proceed.  Check if we are running with SST or from Python.
#
if __name__ == "__main__":
	try:
		import sst
		SST = True
	except:
		SST = False

	# Construct a DeviceGraph and put pingpong into it, then flatten the graph
	# and make sure the connections are valid
	graph = DeviceGraph()
	graph.add(pingpong("PingPong", 5))
	graph = graph.flatten()
	graph.verify_links()

	builder = BuildSST()

	if SST:
		# If running within SST, generate the SST graph
		builder.build(graph)
	else:
		# generate a graphviz dot file and json output for demonstration
		graph.write_dot_file("pingpong.gv", title="Ping Pong")
		builder.write(graph, "pingpong.json")
