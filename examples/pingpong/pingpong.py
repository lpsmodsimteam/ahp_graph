"""Simple example of two SST components playing pingpong with messages."""

import os
import sys

from PyDL import *


@sstlib("pingpong.Ping")
@port("inout", Port.Single)
class Ping(Device):
    """Ping Device: has a Name and a Model type."""

    def __init__(self, name, size, **kwargs):
        """Size parameter is stored as the model attribute of a device."""
        super().__init__(name, size, kwargs)


@sstlib("pingpong.Pong")
@port("inout", Port.Single)
class Pong(Device):
    """Pong Device."""

    def __init__(self, name, **kwargs):
        """No model for Pong."""
        super().__init__(name, kwargs)


@assembly
class pingpong(Device):
    """Overall architecture layout."""

    def __init__(self, name, size=10, **kwargs):
        """Size parameter is stored as the model attribute of a device."""
        super().__init__(name, size, kwargs)

    def expand(self):
        """Expand the overall architecture into its components."""
        graph = DeviceGraph()  # initialize a Device Graph
        # add myself to the graph, useful if the assembly has ports
        graph.add(self)

        ping = Ping("Ping", self.attr["model"])  # create a Ping Device
        pong = Pong("Pong")  # create a Pong Device

        # add ping and pong to the graph
        graph.add(ping)
        graph.add(pong)

        # link ping and pong
        graph.link(ping.inout, pong.inout)

        return graph


if __name__ == "__main__":
    """
    If we are running as a script (either via Python or from SST), then
    proceed.  Check if we are running with SST or from Python.
    """
    try:
        import sst

        SST = True
    except ImportError:
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
        graph.write_dot_file("pingpong", draw=True, ports=True)
        builder.write(graph, "pingpong.json")
