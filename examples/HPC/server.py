"""
Collection of PyDL Device wrappers around SST Components
"""
from PyDL.examples.HPC.processor import Processor
from PyDL import *


@sstlib('memHierarchy.MemController')
@port('direct_link', Port.Single, 'simpleMem', Port.Required)
class MemController(Device):
    """MemController"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize."""
        parameters = {
            "bus_frequency": "1GHz",
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@sstlib('memHierarchy.simpleMem')
class simpleMem(Device):
    """simpleMem"""

    def __init__(self, name: str, attr: dict = None):
        """Initialize."""
        parameters = {
            "bus_frequency": "1GHz",
        }
        if attr is not None:
            parameters.update(attr)
        super().__init__(name, attr=parameters)


@assembly
@port('network', Port.Single, 'network', Port.Optional)
class Server(Device):
    """Server constructed of a processor and some memory."""

    def __init__(self, name, model, datasheet):
        """Store our name"""
        super().__init__(name, model)
        self.datasheet = datasheet

    def expand(self):
        """Expand the server into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)

        return graph
